# SlideLoader
Tool for loading slide metadata for caMicroscope

## Architecture
SlideLoader has five main components: Config, Controller, Extractor, Reader, and Requester

* *Config* reads configuration data from a config file.
* *Reader* reads data from a file regarding which slide files to load and information not present in the file's slide metadata
* *Extractor* extracts slide file metadata
* *Controller* Launches instances of requestor with one slide each
* *Requestor* Checks if a slide with the assigned id exists, and posts those which do not


# TODO, documentation
* precedence of metadata, manifest, and global
* existence check, check_url and exist_check_test
* a description of the config fields
* better default config while at it
* dry_run
* image thumbnail generation
