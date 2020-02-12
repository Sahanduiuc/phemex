publish:
	python3 setup.py sdist bdist_wheel
	twine upload dist/*
	rm -rf build dist .egg phemex.egg-info

.PHONY: publish