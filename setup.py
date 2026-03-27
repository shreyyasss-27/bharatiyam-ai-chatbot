from setuptools import setup, find_packages

setup(
    name="bharatiyam",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'flask',
        'langdetect',
        'sentence-transformers',
        'faiss-cpu',
        'numpy',
        'python-dotenv',
        'transformers',
    ],
)
