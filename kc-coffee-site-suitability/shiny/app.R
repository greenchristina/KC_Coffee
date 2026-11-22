# KC coffeehouse site-suitability map.
# Run from the project root:  shiny::runApp("shiny")
# Reads data/processed/ written by src/05_score.py. Scores are recomputed live from the five factor
# percentiles, so moving a weight slider re-ranks every tract without re-running Python.

library(shiny)
library(bslib)
library(leaflet)
library(sf)
library(dplyr)

data_dir <- file.path("..", "data", "processed")
tracts <- st_read(file.path(data_dir, "tracts_scored.geojson"), quiet = TRUE) |>
  mutate(across(c(scored, income_imputed, income_topcoded), as.logical))
cafes <- st_read(file.path(data_dir, "cafes.geojson"), quiet = TRUE) |>
  filter(as.logical(coffee_competitor))

factors <- c(
  income      = "Median household income",
  growth      = "Population growth",
  workers     = "Daytime workers",
  access      = "Residents within 10-min drive",
  competition = "Low competitor density"
)
default_w <- c(income = 25, growth = 15, workers = 20, access = 20, competition = 20)
counties <- sort(unique(tracts$county))

# Sequential green ramp matching the portfolio site (light = low score, dark = high); excluded tracts in grey.
score_ramp <- c("#d3f2e8", "#b8d9b8", "#7fb99a", "#3d8c68", "#006241", "#00432c")
excluded_fill <- "#e1e0d9"
cafe_cols <- c(chain = "#eb6834", independent = "#6250d6", unknown = "#898781")

fmt_money <- function(x) ifelse(is.na(x), "n/a", paste0("$", formatC(x, format = "d", big.mark = ",")))
fmt_int   <- function(x) formatC(round(x), format = "d", big.mark = ",")
fmt_pct   <- function(p) ifelse(is.na(p), "", sprintf(" <span style='color:#52514e'>(%d<sup>th</sup> pct)</span>", round(p * 100)))

ui <- page_sidebar(
  title = "Kansas City coffeehouse site suitability: census tracts",
  sidebar = sidebar(
    width = 310,
    h6("Factor weights"),
    lapply(names(factors), function(k)
      sliderInput(paste0("w_", k), factors[[k]], min = 0, max = 50, value = default_w[[k]], step = 5)),
    textOutput("weight_note", container = function(...) div(class = "small text-muted", ...)),
    actionButton("reset", "Reset weights", class = "btn-sm btn-outline-secondary"),
    hr(),
    checkboxGroupInput("counties", "Counties", choices = counties, selected = counties),
    numericInput("top_n", "Highlight top N tracts", value = 10, min = 1, max = 50),
    downloadButton("download", "Download ranking (CSV)", class = "btn-sm")
  ),
  card(full_screen = TRUE, card_header("Suitability score (0-100, higher is better)"),
       leafletOutput("map", height = 560)),
  card(card_header(textOutput("table_title", inline = TRUE)), tableOutput("top_table"))
)

server <- function(input, output, session) {
  weights <- reactive(sapply(names(factors), function(k) input[[paste0("w_", k)]]))

  observeEvent(input$reset, for (k in names(factors)) updateSliderInput(session, paste0("w_", k), value = default_w[[k]]))

  output$weight_note <- renderText({
    w <- weights()
    if (sum(w) == 0) return("All weights are 0: using equal weights.")
    paste("Share of score:", paste0(round(100 * w / sum(w)), "%", collapse = " / "))
  })

  ranked <- reactive({
    w <- weights(); if (sum(w) == 0) w[] <- 1
    pct <- as.matrix(st_drop_geometry(tracts)[paste0("pct_", names(factors))])
    d <- tracts
    d$score <- as.vector(pct %*% w) / sum(w) * 100
    d <- d[d$county %in% input$counties, ]
    d$rank <- NA_integer_
    d$rank[d$scored] <- rank(-d$score[d$scored], ties.method = "min")
    d
  })

  output$map <- renderLeaflet({
    leaflet(options = leafletOptions(preferCanvas = TRUE)) |>
      addProviderTiles(providers$Esri.WorldGrayCanvas) |>  # neutral, keyless basemap
      setView(-94.58, 39.05, zoom = 10) |>
      addMapPane("tracts", zIndex = 410) |>
      addMapPane("cafes", zIndex = 420) |>  # cafes always draw above the redrawn tract layer
      addCircleMarkers(data = cafes, group = "Coffee competitors", options = pathOptions(pane = "cafes"),
                       radius = 4, weight = 1.5, color = "#ffffff",
                       opacity = 1, fillColor = unname(cafe_cols[cafes$segment]), fillOpacity = 1,
                       label = ~paste0(std_name, " (", segment, ")")) |>
      addLegend("bottomleft", colors = unname(cafe_cols[c("chain", "independent")]),
                labels = c("Chain cafe", "Independent cafe"), title = "Competitors", group = "Coffee competitors") |>
      addLayersControl(overlayGroups = "Coffee competitors", options = layersControlOptions(collapsed = FALSE))
  })

  observe({
    d <- ranked()
    top <- d$scored & !is.na(d$rank) & d$rank <= input$top_n
    rng <- range(d$score[d$scored], na.rm = TRUE)
    pal <- colorNumeric(score_ramp, domain = rng)
    fill <- ifelse(d$scored, pal(pmin(pmax(d$score, rng[1]), rng[2])), excluded_fill)

    hover <- ifelse(d$scored,
                    sprintf("<b>%s</b>, %s<br>Score %.0f &middot; rank %d of %d", d$NAMELSAD, d$county,
                            d$score, d$rank, sum(d$scored)),
                    sprintf("<b>%s</b>, %s<br>%s", d$NAMELSAD, d$county, d$exclude_reason))
    flags <- paste0(ifelse(d$income_imputed, "<br><i>Income suppressed by Census: neighbouring tracts' median used.</i>", ""),
                    ifelse(d$income_topcoded, "<br><i>Income is top-coded at $250,001: true value is higher.</i>", ""))
    popup <- ifelse(d$scored, paste0(
      hover, "<hr style='margin:4px 0'>",
      "Median income: ", fmt_money(d$median_income), fmt_pct(d$pct_income), "<br>",
      "Population growth: ", sprintf("%+.1f%%", d$growth_pct), fmt_pct(d$pct_growth), "<br>",
      "Jobs in tract: ", fmt_int(d$jobs), " (", fmt_int(d$jobs_per_sqmi), "/sq mi)", fmt_pct(d$pct_workers), "<br>",
      "Residents within 10 min: ", fmt_int(d$reach_pop_10), fmt_pct(d$pct_access), "<br>",
      "Competitors within 10 min: ", d$cafes_10, " (", d$chain_cafes_10, " chain); ",
      sprintf("%.1f per 10k residents", d$cafes_per_10k), fmt_pct(d$pct_competition), "<br>",
      "Nearest competitor: ", sprintf("%.1f min drive", d$nearest_cafe_min), flags), hover)

    leafletProxy("map", data = d) |>
      clearGroup("Tracts") |> removeControl("score_legend") |>
      addPolygons(group = "Tracts", options = pathOptions(pane = "tracts"), fillColor = fill, fillOpacity = 0.75,
                  color = ifelse(top, "#0b0b0b", "#ffffff"), weight = ifelse(top, 2.5, 0.5), opacity = 1,
                  label = lapply(hover, htmltools::HTML), popup = popup,
                  highlightOptions = highlightOptions(weight = 3, color = "#52514e", bringToFront = TRUE)) |>
      addLegend("bottomright", pal = pal, values = rng, title = "Score", layerId = "score_legend",
                labFormat = labelFormat(digits = 0))
  })

  top_rows <- reactive({
    d <- st_drop_geometry(ranked())
    d <- d[d$scored, ]
    d <- d[order(d$rank), ]
    data.frame(
      Rank = d$rank, Tract = sub("Census Tract ", "", d$NAMELSAD), County = d$county,
      Score = sprintf("%.1f", d$score),`Median income` = fmt_money(d$median_income),
      `Pop. growth` = sprintf("%+.1f%%", d$growth_pct), `Jobs / sq mi` = fmt_int(d$jobs_per_sqmi),
      `Residents in 10 min` = fmt_int(d$reach_pop_10), `Competitors in 10 min` = d$cafes_10,
      GEOID = d$GEOID, check.names = FALSE)
  })

  output$table_title <- renderText(sprintf("Top %d tracts", input$top_n))
  output$top_table <- renderTable(head(top_rows(), input$top_n), striped = TRUE, spacing = "s", align = "l")
  output$download <- downloadHandler(
    filename = function() "kc_coffee_site_ranking.csv",
    content = function(file) write.csv(top_rows(), file, row.names = FALSE))
}

shinyApp(ui, server)
