# ==============================================================================
# World map of migration rates by country of affiliation in 2022 (Supplementary
# Appendix 6). Input: table_s3_countries_v2.csv written by
# r2r_check_nationalities_v2.ipynb. Countries with fewer than MIN_N identified
# researchers are shown in mid grey, countries without affiliation data in light
# grey; the colour scale is capped at CAP percent.
#   Rscript migration_map.R
# ==============================================================================

suppressMessages({library(ggplot2); library(maps); library(dplyr)})
tab <- read.csv("/home/lauer/projects/Mastodon/code/revision/r2r_check_nationalities/table_s3_countries_v2.csv", stringsAsFactors = FALSE)
MIN_N <- 100; CAP <- 4
iso <- maps::iso3166; iso$region <- trimws(sub("\\(.*$", "", iso$mapname))
lookup <- iso %>% distinct(region, .keep_all = TRUE) %>% select(region, a2)
world <- map_data("world") %>% filter(region != "Antarctica") %>% left_join(lookup, by = "region") %>%
  left_join(tab %>% transmute(a2 = country_code, total, rate = migration_rate_pct), by = "a2") %>%
  mutate(cls = case_when(is.na(total) ~ "nodata", total < MIN_N ~ "fewdata", TRUE ~ "rate"),
         rate_plot = ifelse(cls == "rate", pmin(rate, CAP), NA_real_))
cat("coloured:", n_distinct(world$a2[world$cls == "rate"]), "| fewer than", MIN_N, ":", n_distinct(world$a2[world$cls == "fewdata"]), "| no data:", n_distinct(world$region[world$cls == "nodata"]), "\n")
p <- ggplot() +
  geom_polygon(data = filter(world, cls == "nodata"),  aes(long, lat, group = group), fill = "#f2f2f2", colour = "white", linewidth = 0.15) +
  geom_polygon(data = filter(world, cls == "fewdata"), aes(long, lat, group = group), fill = "#cfcfcf", colour = "white", linewidth = 0.15) +
  geom_polygon(data = filter(world, cls == "rate"),    aes(long, lat, group = group, fill = rate_plot), colour = "white", linewidth = 0.15) +
  scale_fill_gradient(low = "#f6e6ee", high = "#6e2550", limits = c(0, CAP), breaks = 0:4, labels = c("0%", "1%", "2%", "3%", "≥ 4%"),
                      name = "Migration rate", guide = guide_colourbar(barwidth = 14, barheight = 0.6, title.position = "top", title.hjust = 0.5)) +
  coord_fixed(1.3, ylim = c(-56, 84), expand = FALSE) +
  labs(title = "Migration rate by country of affiliation in 2022",
       caption = sprintf("Countries with fewer than %d identified researchers in mid grey; countries without affiliation data in light grey.", MIN_N)) +
  theme_void() +
  theme(legend.position = "bottom", plot.title = element_text(size = 16, hjust = 0.5, margin = margin(b = 10)),
        legend.text = element_text(size = 11), legend.title = element_text(size = 12),
        plot.caption = element_text(size = 9, colour = "#555555", hjust = 0.5, margin = margin(t = 8)),
        plot.background = element_rect(fill = "white", colour = NA), plot.margin = margin(10, 10, 10, 10))
ggsave("/home/lauer/projects/Mastodon/results/figures/supplementary_migration_map_countries.png", p, width = 11, height = 6.4, dpi = 300)
cat("saved\n")
