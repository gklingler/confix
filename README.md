# confix 
... a tiny tool that simplifies backup, versioning and distributing your config/dot files on Linux.

The idea is simple: confix moves files to a directory (the confix repository) and replace the original files with a symlinks to the files in the confix repo.

Confix provides some convenient commands for operations on such a confix repo: adding/linking/merging/removing/listing files.

Keeping the configuration files in a dedicated directory simplifies backup, versioning and distributing them: e.g. version/sync confix repo with git, or sync it to an other PC with any file sync tool.

```
usage: confix [-h] {info,ls,setRepo,add,rm,setMergeTool,link,unlink,merge} ...

positional arguments:
  {info,ls,setRepo,add,rm,setMergeTool,link,unlink,merge}
    info                shows the current confix repo path
    ls                  lists the files in the confix repo and indicates if
                        the file is installed by a "+"
    setRepo             sets the confix repo to the given path
    add                 copies a file to the confix repo and replaces the
                        original file with a symlink
    rm                  removes a file from the confix repo
    setMergeTool        sets the merge tool
    link                creates a link to an existing file in the confix repo
    unlink              unlinks a file from the confix repo
    merge               opens the given file and the file in the confix repo
                        in the configured MERGE_TOOL

optional arguments:
  -h, --help            show this help message and exit
```

### example use case

You want to share your some dot files between your PC and your Laptop: This would be the typical workflow with confix + git. 

1.) Setup confix on your PC, add some files to the confix repo and push them to the git remote:
```
create a git repository that will function as confix repo (e.g. at github)
clone your git repo to ~/.confixRepo

confix setRepo ~/.confixRepo     # tell confix to use this directory as confix repo
confix add ~/.gitconfig          # moves .gitconfig to the confix repo and creates the symlink
confix add ~/.i3/config          # moves .i3/config to the confix repo and creates the symlink
confix ls                        # list files in the confix repo

add, commit (and push) the files to git.
```

2.) On the Laptop, clone the git repo, tell confix to use it as confix repo and link the files:

```
clone your git repo to ~/.confixRepo
confix setRepo ~/.confixRepo     # tell confix to use this directory as confix repo
confix ls                        # list files in the confix repo
confix link ~/.gitconfig         # create a symlink from ~/.gitconfig to the file in the confix repo
confix add ~/.i3/config          # create a symlink from ~/.i3/config to the file in the confix repo
```

