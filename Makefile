
extract-from-kdenlive:
	- rm out/*.mp3
	cd out/macro-output && $(MAKE) clean
	cd out/final && $(MAKE) clean
	python extract.py
