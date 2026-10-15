import pandas as pd
from tqdm import tqdm
from bertopic import BERTopic
import numpy as np
from sentence_transformers import SentenceTransformer
import json
from sklearn.metrics.pairwise import cosine_similarity
from tqdm import tqdm
from joblib import Parallel, delayed
from scipy.stats import pearsonr

from utils.utils import (
    get_path,
)

from utils.data_loaders import (
    load_posts_prepost_main,
    load_posts_pre_post_split_exploded_list,
    load_posts_pre_post_split_embeddings,
    load_openalex_discipline_labels,
    load_posts_pre_post_split_,
    load_posts_pre_post_split_exploded,
    load_doc_text_to_disciplines_text_df_50,
    load_openalex_discipline_labels_embeddings,
    load_posts_research_aggregated_main,
)


def prep_posts_prepost_split(cfg):
    """
    Final postprocessing of pre-post split df for immediacy calculation.

    1.  removing some remaining posts without text content and saving df with
        index as column for a later merging step.
    2.  explode the df based on the column "description_text_combined_all" so
        that there is one post per row. Save exploded df and also save list of
        exploded text column to feed to sentence transformers.

    Returns:
        posts_pre_post_split_exploded_list (list): List of exploded posts to
        directly feed into precomputation of embeddings
    """

    posts_pre_post_split = load_posts_prepost_main(cfg)

    # remove posts without text content from list of posts
    posts_pre_post_split["contains_original_posts"] = (
        posts_pre_post_split.text_combined_original.apply(lambda x: len(x) > 0)
    )  # for distinguishing between original posts and all posts
    posts_pre_post_split["description_text_combined_all"] = posts_pre_post_split[
        "description_text_combined_all"
    ].apply(lambda x: [elem for elem in x if len(elem) > 0])
    posts_pre_post_split["text_combined_original"] = posts_pre_post_split[
        "text_combined_original"
    ].apply(lambda x: [elem for elem in x if len(elem) > 0])

    # Sanity check: Are there people who dont have any posts left after removing
    # posts without text?
    if posts_pre_post_split.description_text_combined_all.apply(
        lambda x: len(x) == 0
    ).any():
        raise ValueError("Error: Person(s) without posts")

    # store index as column for later aggregation on a person level after
    # exploding for sentence tranformer
    posts_pre_post_split.reset_index(inplace=True)

    # save df with posts without text content removed, and with index as column
    path_posts_pre_post_split_ = get_path(
        cfg, "processed", "social_impact", "posts_pre_post_split_.json"
    )
    posts_pre_post_split.to_json(
        path_posts_pre_post_split_, orient="records", lines=True
    )

    # explode list column: the df contains the posts for each person in a list
    # in a single row. we explode this post column such that new rows are
    # created, each with a single post.
    posts_pre_post_split_exploded = posts_pre_post_split.explode(
        "description_text_combined_all"
    )

    # save exploded df
    path_posts_pre_post_split_exploded = get_path(
        cfg, "processed", "social_impact", "posts_pre_post_split_exploded.json"
    )
    posts_pre_post_split_exploded.to_json(
        path_posts_pre_post_split_exploded, orient="records", lines=True
    )

    # convert documents column to list
    posts_pre_post_split_exploded_list = posts_pre_post_split_exploded[
        "description_text_combined_all"
    ].to_list()

    # save list of documents to JSON file
    path_posts_pre_post_split_exploded_list = get_path(
        cfg, "processed", "social_impact", "posts_pre_post_split_exploded_list.json"
    )
    with open(path_posts_pre_post_split_exploded_list, "w") as file:
        json.dump(posts_pre_post_split_exploded_list, file)

    return posts_pre_post_split_exploded_list


def precompute_embeddings(cfg, posts_pre_post_split_exploded_list):
    """
    Precompute and save embeddings for all posts for fast lookup using Sentence
    Transformers package. Embeddings are saved as numpy array.

    Returns:
        None
    """

    # load multilingual model
    embedding_model = cfg["bertopic_params"]["embedding_model"]
    sentence_model = SentenceTransformer(embedding_model)

    # compute embeddings
    docs_embeddings = sentence_model.encode(
        posts_pre_post_split_exploded_list,
        show_progress_bar=True,
    )

    # save embeddings
    path_docs_embeddings = get_path(
        cfg, "processed", "social_impact", "posts_pre_post_split_embeddings.npy"
    )
    np.save(path_docs_embeddings, docs_embeddings)


def prep_zeroshot_topic_modelling(cfg, cosine_thresh=0.5):
    """
    Map each post to only those Open Alex research disciplines labels for which
    cosine similarity threshold is exceeded (similarity between post embeddings
    and discipline embeddings > cosine_thresh).

    1.  compute and save the embeddings for the Open Alex list (fast).
    2.  process each document, comparing its embedding with each discipline
    3.  save the mapping of document text to discipline labels that exceed threshold

    Returns:
        None
    """

    # load documents
    docs = load_posts_pre_post_split_exploded_list(cfg)

    # load embeddings of documents
    docs_embeddings = load_posts_pre_post_split_embeddings(cfg)

    # load OpenAlex discipline labels (long)
    zeroshot_topics_df = load_openalex_discipline_labels(cfg)
    zeroshot_topics_list = zeroshot_topics_df["long_label"].to_list()

    # compute and save embeddings of long labels of dicisplines
    sentence_model = SentenceTransformer(
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    zeroshot_topics_list_embeddings = sentence_model.encode(
        zeroshot_topics_list,
        show_progress_bar=True,
    )
    path_embeddings = get_path(
        cfg, "processed", "social_impact", "micro_cluster_embeddings_long.npy"
    )
    np.save(path_embeddings, zeroshot_topics_list_embeddings)

    def process_document(doc_text, doc_embedding, cosine_thresh):
        """
        Nested function to process a document, comparing its embedding with each
        discipline embedding, returning document text along with only those
        discipline labels that exceed cosine similarity theshold.
        """

        # Calculate cosine similarity between this document and all discipline embeddings
        similarities = cosine_similarity(
            [doc_embedding], zeroshot_topics_list_embeddings
        )[0]

        # Find indices of disciplines with similarity above the threshold
        relevant_disciplines_idx = [
            idx
            for idx, similarity in enumerate(similarities)
            if similarity > cosine_thresh
        ]

        # Convert indices to discipline labels
        relevant_disciplines_labels = [
            zeroshot_topics_list[idx] for idx in relevant_disciplines_idx
        ]

        return doc_text, relevant_disciplines_labels

    # Process each document, using joblib for parallel processing
    results = Parallel(n_jobs=-1)(
        delayed(process_document)(doc_text, doc_embedding, cosine_thresh)
        for doc_text, doc_embedding in tqdm(zip(docs, docs_embeddings), total=len(docs))
    )
    doc_text_to_disciplines_text_df = pd.DataFrame(
        results, columns=["document_text", "disciplines"]
    )  # convert list of tuples to pandas df

    # save df
    path_doc_text_to_disciplines_text_df = get_path(
        cfg, "processed", "social_impact", "doc_text_to_disciplines_text_df_50.json"
    )
    doc_text_to_disciplines_text_df.to_json(
        path_doc_text_to_disciplines_text_df, orient="records", lines=True
    )


def prep_BERTopic(cfg):
    """
    Function for final preparation for BERTopic.

    Remove posts that have zero mapped disciplines, i.e. where cosine similarity
    for none of the disciplines exceeded the threshold. Removing from:
    document-dicipline mapping, exploded pre-post-split, and embeddings.

    Unexplode (aggregate on a person level) and save exploded pre-post-split so
    that we have one row per person again - used again after BERTopic.

    Returns:
        docs: List of filtered post documents.
        docs_embeddings: Embeddings of filtered documents.
        zeroshot_topics_list: List of OpenAlex discipline labels.
    """

    # load pre-post split posts
    # posts_pre_post_split = load_posts_pre_post_split_(cfg)

    # load pre-post split exploded posts
    posts_pre_post_split_exploded = load_posts_pre_post_split_exploded(cfg)

    # load documents
    docs = load_posts_pre_post_split_exploded_list(cfg)

    # load pre-computed embeddings
    docs_embeddings = load_posts_pre_post_split_embeddings(cfg)

    # load documents to disciplines mapping based on cosine similarity threshold
    doc_text_to_disciplines_text_df = load_doc_text_to_disciplines_text_df_50(cfg)

    # load OpenAlex discipline labels (long) and embeddings
    zeroshot_topics_df = load_openalex_discipline_labels(cfg)
    zeroshot_topics_list = zeroshot_topics_df["long_label"].to_list()
    # zeroshot_topics_list_embeddings = load_openalex_discipline_labels_embeddings(cfg)

    # sanity check
    if not doc_text_to_disciplines_text_df.document_text.equals(
        posts_pre_post_split_exploded.description_text_combined_all
    ):
        raise ValueError("Document texts don't match")

    # drop posts that don't exceed the cosine similarity threshold (i.e., no
    # disciplines assigned) from documents to disciplines mapping
    len_before = len(posts_pre_post_split_exploded)
    mask = doc_text_to_disciplines_text_df.disciplines.apply(lambda x: len(x) > 0)
    doc_text_to_disciplines_text_df = doc_text_to_disciplines_text_df[mask]
    print(
        f"Dropped {len_before - len(doc_text_to_disciplines_text_df)} / {len_before} posts that did not exceed the cosine similarity threshold"
    )

    # drop the same posts from our pre-post split df
    posts_pre_post_split_exploded = posts_pre_post_split_exploded[mask]

    # drop the same posts from docs list
    mask_list = mask.tolist()
    docs = [doc for doc, m in zip(docs, mask_list) if m]

    # drop embeddings of the same posts
    docs_embeddings = docs_embeddings[mask]

    # unexplode posts so that we have one row per person again
    posts_research_aggregated = posts_pre_post_split_exploded.groupby("index").agg(
        {
            "description_text_combined_all": list,  # aggregated posts in list
            "id": "first",  # take only first id (all the same anyway)
            "twitter_username": "first",
            "is_migrated": "first",
            "description": "first",
            "description_is_valid": "first",
            "text_combined_original": "first",
            "contains_original_posts": "first",
        }
    )

    # save df with unexploded posts
    path_posts_research_aggregated = get_path(
        cfg, "processed", "social_impact", "posts_research_aggregated.json"
    )
    posts_research_aggregated.to_json(
        path_posts_research_aggregated, orient="records", lines=True
    )

    return docs, docs_embeddings, zeroshot_topics_list


def run_zeroshot_BERTopic(cfg, docs, docs_embeddings, zeroshot_topics_list):
    """
    Run zero-shot BERTopic on the documents.

    Returns:
        topics: List of topics for each document
        probs: List of probabilities for each document
    """

    # compute topic model
    topic_model = BERTopic(
        embedding_model=cfg["bertopic_params"]["embedding_model"],
        min_topic_size=cfg["bertopic_params"]["min_topic_size"],
        calculate_probabilities=cfg["bertopic_params"]["calculate_probabilities"],
        zeroshot_topic_list=zeroshot_topics_list,
        zeroshot_min_similarity=cfg["bertopic_params"]["zeroshot_min_similarity"],
    )

    # get topics and probs
    # NOTE: because zero-shot topic modeling is essentially merging two
    # different topic models, the probs will be empty initially. If you want to
    # have the probabilities of topics across documents, you can run
    # topic_model.transform on your documents to extract the updated probs.
    topics, probs = topic_model.fit_transform(docs, docs_embeddings)

    # save model
    path_topic_model = get_path(
        cfg, "processed", "social_impact", "BERTopic_zeroshot_50"
    )
    topic_model.save(
        path_topic_model,
        serialization="safetensors",
        save_ctfidf=True,
        save_embedding_model=cfg["bertopic_params"]["embedding_model"],
    )

    return topics, probs


def get_doc_topic_probs(cfg):
    """
    Get document-topic probabilities per person per post, and average them to
    obtain a single document-topic probability vector per person, saved to disk.

    Document-topic probabilities are obtained by using BERTopic's .transform()
    on aggregated posts per person.

    Returns:
        None
    """

    # load data
    posts_research_aggregated = load_posts_research_aggregated_main(cfg)

    # load model
    path_topic_model = get_path(
        cfg, "processed", "social_impact", "BERTopic_zeroshot_50"
    )
    topic_model = BERTopic.load(path_topic_model)

    def average_probs(posts_list):
        # get probs for all posts by person
        probs = topic_model.transform(posts_list)
        # get mean of these probabilities
        avg_probs = np.mean(probs[1], axis=0)
        return avg_probs

    # apply function to calculate probs using progress bar
    tqdm.pandas(desc="Processing rows")
    posts_research_aggregated["average_probs"] = posts_research_aggregated[
        "description_text_combined_all"
    ].progress_apply(average_probs)

    # save df with average probs per person
    path_posts_research_aggregated_probs = get_path(
        cfg, "processed", "social_impact", "posts_research_aggregated_probs.json"
    )
    posts_research_aggregated.to_json(
        path_posts_research_aggregated_probs, orient="records", lines=True
    )

    # NOTE: This comment explains that one can use .transform to get the cosine
    # similarities in zero-shot topic modeling:
    # https://github.com/MaartenGr/BERTopic/issues/1928 Having said that, you
    # could also simply save the model using .safetensors and then load the
    # model. What happens is that the underlying dimensionality reduction and
    # cluster models are removed. Now, whenever you run .transform, it will use
    # the cosine similarity between topic and document embeddings to generate
    # the exact same similarity matrix that you have created manually. You can
    # use that output to assign a single document to multiple topics using the
    # same threshold you specified for zero-shot topic modeling.


# TODO: The following function does not work, some problem with parrallel apply.
# maybe bc of nested df.iterrrows() in function, stuck at 0% progress. Works
# after moving the function to main.py for now.
# def calculate_immediacy(profiles_researchers_df):
#     """
#     Calculate immediacy (i.e., similarity of interests) of a user and the
#     followed influencers. Specifically, calculate mean correlation of (mean)
#     document-topic probabilities (i.e., across all posts) of the user with
#     probabilities of followed influencers. Do this for all rows (users).
#     """

#     def calculate_immediacy_row(row):

#         followed_influencers_IDs = row["followed_influencer_ids_remaining"]

#         # if no followed influencers, return nan
#         if not followed_influencers_IDs:
#             return np.nan

#         # subset of df with only followed influencers
#         filtered_df = profiles_researchers_df[
#             profiles_researchers_df["id"].isin(followed_influencers_IDs)
#         ]

#         # for each followed influencer, correlate the user's average probs with the
#         # influencer's average probs
#         correlations_probs_user_influencers = []
#         for index, row_filt in filtered_df.iterrows():
#             correlation, _ = pearsonr(row["average_probs"], row_filt["average_probs"])
#             if not np.isnan(correlation):  # exclude cases of zero variance (0 cases)
#                 correlations_probs_user_influencers.append(correlation)

#         # if no correlations, return nan (should only occur if all correlations were
#         # based on zero variance, so empty list) (0 cases)
#         if not correlations_probs_user_influencers:
#             return np.nan

#         # calculate the mean of the correlations
#         correlations_probs_user_influencers_mean = np.mean(
#             correlations_probs_user_influencers
#         )

#         print("completed one iteration")

#         return correlations_probs_user_influencers_mean

#     # apply function, calculating strength and number of sources for each researcher
#     profiles_researchers_df["SI_I"] = profiles_researchers_df.parallel_apply(
#         calculate_immediacy_row, axis=1
#     )

#     return profiles_researchers_df
