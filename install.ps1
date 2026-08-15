python -3.13 -m venv .venv

& .\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip

python -m pip install --only-binary=llama-cpp-python "llama-cpp-python==0.3.34" --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu

python -m pip install hf_xet

python -m pip install -e .

python .\run.py