# NCAA Swimming Analysis

It feels like swimmers, especially in the NCAA, are getting faster, well, faster! This project is my attempt to try and figure out if that's the case. There are a few hypotheses I could test to evaluate whether this trend. The first thing I want to understand is what is happening with NCAA Records -- are they being broken at a faster rate or by greater margins? 

I first downloaded a CSV of [NCAA Record Progression from USA Swimming](https://www.usaswimming.org/times/otherorganizations/ncaa-division-i), but it turns out there is a ton of data missing.

Filling in the gaps is tricky, but the best approach I could come up with was scraping the NCAA Championship results from the [SwimSwam results archive](https://swimswam.com/swimswam-meet-results-archive/), since each year's results included the NCAA record in each event as of that season. The PDFs in the results archive had searchable text dating back to 2002, although in 2004 NCAA championships were swum in Short Course Meters (rather than yards) so I've excluded those records from the data set.

I removed duplicates from the scraped data, then combined with USA Swimming data, removed duplicates again, and now I believe I've compiled [the most robust record of NCAA Division 1 Swimming record progression](https://github.com/KendrickMcD/NCAA_Swimming_Analysis/blob/main/ncaa_record_progression.csv) available!

In the scripts folder are the python scripts I used to scrape and clean data (both from USA Swimming and SwimSwam), and in the notebooks folder are Jupyter notebooks I've used to work with the data. This project is still incomplete, as there's plenty of interesting analysis of the records left to do. If you have suggestions, please get in touch: mconald[dot]kend[at]gmail.com.
