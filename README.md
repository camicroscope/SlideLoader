# SlideLoader
Tool for loading slides and getting slide metadata using openslide

## Setting up

When used outside of caMicroscope/Distro Docker, the [BFBridge](https://github.com/camicroscope/BFBridge) folder needs to copied to this repository manually. (Not only its contents, but making it a subfolder of this repository)

## Usage

### Upload

Uploading is done in chunks due to the generally large size of the files involved. To upload a slide, you must begin, continue, and finish the upload, as noted in the subsections below.

#### Begin

Calling a post to the begin route (http://\<service url base\>/upload/start) will generate a token and a corresponding empty file in the uploading directory. This token is then used for the continue and finish steps.

Note that a file in the uploading directory can be modified by anyone with the token.

#### Continue

Post filedata encoded in base64 as "data" and the offset as "offset" in a json document in the body to the continue route for the token given (http://\<service url base\>/upload/continue/<\token\>). The data is then written to the temporary file in the uploading directory starting at the given offset, in bytes.

#### Finish

To prevent further modification to the file, call the finish route (http://\<service url base\>/upload/finish/<\token\>) with the destination filename as "filename" in a json document in the body. In most cases where this fails (such as a rejection for a filename being taken), the temporary file is unchanged so a user can simply try again.

### Multiple Image Upload
Place your images into a directory on your filesystem.
Then use upload.sh to upload the file.  Pass your file path as a parameter.
Example: `./upload.sh /path/to/svs/files`

### Get a Single Image's Metadata

See, for example, http://\<service url base\>/data/one/\<slide filename\>

This returns the openslide metadata for the given slide.
### Get metadata for a list of image

See, for example http://\<service url base\>/data/many/["\<slide1_filename\>", "\<slide2_filename\>"]

This returns the metadata for each slide.

### Loading to caMicroscope

This tool does not communicate with bindaas/drupal/whatever backend is used for slide metadata. Since these data backends have their own method for posting slide metadata, that should be used. This tool can be used as a service oriented way to get slide metadata to then post to the data backend.
