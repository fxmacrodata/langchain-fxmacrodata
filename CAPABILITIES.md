# What the tools cover

`fxmacrodata_tools()` returns one LangChain tool for each public GET route.

| Data | Tool |
| --- | --- |
| Catalogue | `fxmacrodata_data_catalogue_currency` |
| Macro history | `fxmacrodata_announcements_currency_indicator` |
| Release calendar | `fxmacrodata_calendar_currency` and the other `fxmacrodata_calendar_*` tools |
| Predictions | `fxmacrodata_predictions_*` |
| Press headlines | `fxmacrodata_press_releases_currency` |
| FX spot, reference rates and sessions | `fxmacrodata_forex_*` and `fxmacrodata_fx_*` |
| Market sessions | `fxmacrodata_market_sessions` |
| COT and positioning | `fxmacrodata_cot_*` and `fxmacrodata_positioning_*` |
| Commodities, curves, factors and prices | the matching GET tools |
| Event stream | `fxmacrodata_stream_events` |

USD catalogue, USD macro history and the USD release calendar need no API key. Set `FXMACRODATA_API_KEY` when a route requires one.

Product documentation: https://fxmacrodata.com/docs?utm_source=langchain&utm_medium=integration&utm_campaign=langchain-fxmacrodata&utm_content=capabilities-docs
