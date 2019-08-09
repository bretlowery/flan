from flanimport import FlanImport

import os
import glob
import collections
import gzip

try:
    from flan import error
except:
    from flan.flan import error
    pass


class Files(FlanImport):

    def __init__(self, meta, config):
        self.name = self.__class__.__name__
        super().__init__(self.name, meta, config)

    def _load(self, meta):
        try:
            # get spec of template log file(s)
            self.templatelogfiles = meta.templatelogfiles.strip()
            # get each template log file's file creation date
            fd = {}
            for file in glob.glob(self.templatelogfiles):
                cd = os.path.getctime(file)
                fd[cd] = file
            # order the list of template log files by creation date asc (oldest first)
            fod = collections.OrderedDict(sorted(fd.items()))
            for cd, file in fod.items():
                if file[3:].lower() == ".gz" or file[5:].lower() == ".gzip":
                    with gzip.open(file, "rb") as fp:
                        currentfile = fp.readlines()
                        fp.close()
                else:
                    with open(file, "r") as fp:
                        currentfile = fp.readlines()
                        fp.close()
                self.contents = self.contents + [x.strip() for x in currentfile]
            # do something with file
        except IOError as e:
            error("Flan import error when trying to read the template log files: %s" % str(e))
            pass
        return self.contents
