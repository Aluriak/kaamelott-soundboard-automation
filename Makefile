
extract-from-kdenlive:
	- rm out/*.mp3
	- cd out/ && $(MAKE) clean
	- cd out/macro-output && $(MAKE) clean
	python extract.py projet-extraction.kdenlive


clean:
	- cd out/ && $(MAKE) clean
	- cd out/macro-output && $(MAKE) clean
	- cd out/final && $(MAKE) clean
