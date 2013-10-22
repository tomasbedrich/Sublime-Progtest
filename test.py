import sublime, sublime_plugin
import subprocess
import tarfile
import shutil
import os
import os.path as path
from sys import exit
from os.path import join


possibleTestDirs = "CZE", "sample/CZE", "tests", "test-data"
possibleArchives = "sample.tgz", "tests.tgz", "test-data.tgz"


class TestCommand(sublime_plugin.ApplicationCommand):

    def __init__(self):
        self.output = None

    def log(self, data, erease=False):
        """Logging the output to console."""
        if not self.output:
            self.output = _getWin().create_output_panel("test")
            _getWin().run_command("show_panel", {"panel": "output.test"})
        if erease:
            self.output.run_command("select_all")
            self.output.run_command("right_delete")
            _getWin().run_command("show_panel", {"panel": "output.test"})
        self.output.run_command("insert", {"characters": data+"\n"})

    def logHr(self, char="-"):
        self.log(char*80)    

    def is_visible(self):
        return self.checkCLang()

    def description(self):
        return "Test"

    def dirDiscovery(self, where=None):
        """Returns a list of existing test directories."""
        if not where:
            where = path.dirname(_getView().file_name())
        return filter(path.exists, map(lambda end: path.join(where, end), possibleTestDirs))

    def archiveDiscovery(self, where=None):
        """Returns a list of existing test archives."""
        if not where:
            where = path.dirname(_getView().file_name())
        return filter(path.exists, map(lambda end: path.join(where, end), possibleArchives))

    def getNoExtName(self, source):
        return path.join(path.dirname(source), path.splitext(source)[0])

    def getExeName(self):
        """Returns a platform-dependant executable name."""
        source = _getView().file_name()
        return self.getNoExtName(source)

    def checkCLang(self):
        view = _getView()
        return view.settings().get("syntax") == "Packages/C++/C.tmLanguage"

    def run(self):
        if not self.checkCLang():
            return

        self.log("Testing strated.", True)
        testRan = False

        # run for archives
        for a in self.archiveDiscovery():
            testRan = True
            self.testArchive(a)

        # run for directories
        for d in self.dirDiscovery():
            testRan = True
            self.testDir(d)
        
        if not testRan:
            self.log("No test data found.")
        
        self.log("Testing ended.")

    def testArchive(self, archive):
        self.log("Testing archive: %s" % archive)

        target = self.getNoExtName(archive)+"_tmp"

        # extract tar file
        self.log("Extracting archive %s to %s" % (archive, target))
        tar = tarfile.open(archive)
        tar.extractall(target)
        tar.close()

        for d in self.dirDiscovery(target):
            self.testDir(d)

        # remove tmp dir
        self.log("Cleaning up.")
        shutil.rmtree(target)

    def testDir(self, testDir):
        self.log("Testing directory: %s" % testDir)
        self.logHr("~")

        dir_name, sub_dirs, files = [v for v in os.walk(testDir)][0]
        alreadyTested = set()
        
        # skip unwanted files
        files = filter(lambda f: not ("win" in f or "tmp" in f or f.startswith(".")), files)

        # for each test file
        for f in files:

            # num of the test
            num = f[:4]

            # prevent passing test twice (IO file with the same number)
            if num not in alreadyTested:
                alreadyTested.add(num)
            else:
                continue

            if not self.testFile(testDir, num):
                self.log("Skipping next tests in the same directory (if any).")
                return False

        return True

    def testFile(self, testDir, num):

        # IO files
        exe = self.getExeName()
        inFile = join(testDir, "%s_in.txt" % num)
        outFile = join(testDir, "%s_out.txt" % num)
        tmpOutFile = join(testDir, "%s_tmp_out.txt" % num)

        # run program
        run = "'%(exe)s' < '%(in)s' > '%(tmpOut)s'" % {"exe": exe, "in": inFile, "tmpOut": tmpOutFile}
        try:
            subprocess.check_output(run, shell=True)
        except subprocess.CalledProcessError as e:
            self.log("Test %s has exit status: %d" % (num, e.returncode))

        # diff output
        diff = "diff '%(out)s' '%(tmpOut)s'" % {"out": outFile, "tmpOut": tmpOutFile}
        try:
            subprocess.check_output(diff, shell=True)
        except subprocess.CalledProcessError as e:
            self.log("Error: Test %s failed." % num)
            self.log(str(e.output, "utf-8").strip())
            self.logHr()
            return False

        self.log("Success: Test %s passed." % num)
        self.logHr()
        return True


# helpers

def _getWin():
    return sublime.active_window()

def _getView():
    return _getWin().active_view()
    