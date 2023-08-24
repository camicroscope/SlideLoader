# Clone github.com/ome/bioformats and run:
# grep -r -e "static final String.*\[\].*SUFFIXES" -e "super.*new String\[\]" -e "super(.*," -A 2 -h | grep " .* .* " | grep -v "=$" | grep -v "{$" | sort -u
# then manually copying extensions, keeping them in order
# The command says: match 'static final String[] XYZ_SUFFIXES' or 'super("XYZFILES", ".xyz")'
# and print next two lines but keep only lines with at least two space and discard those
# ending with "=" or "{" (because in this case only the next line(s) are relevant
# then sort and keep unique lines


# An alternative would be using https://github.com/ome/bioformats/blob/19d7fb9cbfdc1/components/formats-api/src/loci/formats/readers.txt
# Or, https://bio-formats.readthedocs.io/en/latest/supported-formats.html
# For file extensions with multiple dots, here only last part is recorded
# Video, compression formats and duplicates excluded
# https://github.com/ome/bioformats/blob/19d7fb9cbfdc1/components/formats-api/src/loci/formats/readers.txt
# External readers listed on that webpage need to be excluded
# All the rest needs to be included
BIOFORMATS_EXTENSIONS = set(['v3draw', 'ano', 'cfg', 'csv', 'htm', 'rec', 'tim', 'zpo', 'tif', 'dic', 'dcm', 'dicom', 'jp2', 'j2ki', 'j2kr', 'raw', 'ima', 'cr2', 'crw', 'jpg', 'thm', 'wav', 'tiff', 'dv', 'r3d', 'r3d_d3d', 'log', 'mvd2', 'aisf', 'aiix', 'dat', 'atsf', 'tf2', 'tf8', 'btf', 'pbm', 'pgm', 'ppm', 'xdce', 'xml', 'xlog', 'apl', 'tnb', 'mtb', 'im', 'mea', 'res', 'aim', 'arf', 'psd', 'al3d', 'gel', 'am', 'amiramesh', 'grey', 'hx', 'labels', 'img', 'hdr', 'sif', 'afi', 'svs', 'exp', 'h5', '1sc', 'pic', 'scn', 'ims', 'ch5', 'vsi', 'ets', 'pnl', 'htd', 'c01', 'dib', 'cxd', 'v', 'eps', 'epsi', 'ps', 'flex', 'xlef', 'fits', 'fts', 'dm2', 'dm3', 'dm4', 'naf', 'his', 'ndpi', 'ndpis', 'vms', 'txt', 'i2i', 'hed', 'mod', 'inr', 'ipl', 'ipm', 'fff', 'ics', 'ids', 'seq', 'ips', 'ipw', 'frm', 'par', 'j2k', 'jpf', 'jpk', 'jpx', 'klb', 'xv', 'bip', 'sxm', 'fli', 'lim', 'msr', 'lif', 'lof', 'lei', 'l2d', 'mnc', 'stk', 'nd', 'scan', 'vff', 'mrw', 'stp', 'mng', 'nii', 'nrrd', 'nhdr', 'nd2', 'nef', 'obf', 'omp2info', 'oib', 'oif', 'pty', 'lut', 'oir', 'sld', 'spl', 'liff', 'top', 'pcoraw', 'pcx', 'pict', 'pct', 'df3', 'im3', 'qptiff', 'bin', 'env', 'spe', 'afm', 'sm2', 'sm3', 'spc', 'set', 'sdt', 'spi', 'xqd', 'xqf', 'db', 'vws', 'pst', 'inf', 'tfr', 'ffr', 'zfr', 'zfp', '2fl', 'tga', 'pr3', 'dti', 'fdf', 'hdf', 'bif', 'xys', 'html', 'acff', 'wat', 'bmp', 'wpi', 'czi', 'lms', 'lsm', 'mdb', 'zvi', 'mrc', 'st', 'ali', 'map', 'mrcs', 'jpeg', 'png', 'gif', 'ptif'])

OPENSLIDE_EXTENSIONS = set(["svs", "tif", "tiff", "vms", "vmu", "ndpi", "scn", "mrxs", "bif", "svslide", 'dcm', 'dicom'])

# iipsrv support jpg, jpg2000, tiff
# we can also produce pyramids
OTHER_EXTENSIONS = ["jp2", "j2k", "jpx", "tif", "tiff", "tif", "png", "jpg", "jpeg"]

ALLOWED_EXTENSIONS = BIOFORMATS_EXTENSIONS.union(OPENSLIDE_EXTENSIONS).union(OTHER_EXTENSIONS)
