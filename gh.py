import os
from git import Repo


dir = os.getcwd()

repo = Repo(dir)
repo.git.add(update=True)
repo.index.commit("update vargrid")
origin = repo.remote(name='origin')
origin.push()