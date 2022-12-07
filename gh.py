import os
from git import Repo

# gh.py
# YOU MUST HAVE .git FILE CONFIGURED CORRECTLY 
dir = os.getcwd()
repo = Repo(dir)
repo.git.add(update=True)
repo.index.commit("update vargrid")
origin = repo.remote(name='origin')
origin.push()