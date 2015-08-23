#!/usr/bin/env python3
import unittest
import tempfile
from confix import *

class TestConfix(unittest.TestCase):
    def setUp(self):
        self._ROOT_DIR = tempfile.mkdtemp()
        self._REPO_DIR = os.path.join(self._ROOT_DIR, 'dotfiles.git')
        self._BACKUP_DIR = os.path.join(self._ROOT_DIR, 'backup')
        self.cfgx = Confix(self._ROOT_DIR)
        
        # copy all testfiles to a tempdir to avoid destroying them at a test
        self._TESTFILES_DIR = tempfile.mkdtemp()
        shutil.copytree('testFiles', os.path.join(self._TESTFILES_DIR, 'testFiles'), symlinks=True)
        #testfiles:
        self._aSymbolicLink = os.path.join(os.path.abspath(self._TESTFILES_DIR), 'testFiles/configs/aSymbolicLink.conf')
        self._aConfigFile = os.path.join(os.path.abspath(self._TESTFILES_DIR), 'testFiles/configs/aConfigFile.conf')
        self._anotherConfigFile = os.path.join(os.path.abspath(self._TESTFILES_DIR), 'testFiles/configs/anotherConfigFile.conf')
    
    def tearDown(self):
        pass
    
    def test_init(self):
        self.assertTrue(os.path.exists(self._ROOT_DIR))
        self.assertTrue(os.path.exists(self._ROOT_DIR + '/config'))
        self.assertTrue(os.path.exists(self._BACKUP_DIR))
 
    def test_add_non_existing(self):
        with self.assertRaises(ConfixError):
            self.cfgx.add('a/non/existin/path')
     
    def test_add_file_twice(self):
        self.cfgx.add(self._aConfigFile)
        # self._aConfigFile is a link now -> remove it, create a regular file and try to add it again
        os.remove(self._aConfigFile) 
        open(self._aConfigFile, 'a').close()
        with self.assertRaises(ConfixError):
            self.cfgx.add(self._aConfigFile)
        self.assertTrue(os.path.exists(self._aConfigFile) and not os.path.islink(self._aConfigFile), "the original file must still be there")
         
    def test_add_symlink(self):
        # try to add a symlink
        with self.assertRaises(ConfixError):
            self.cfgx.add(self._aSymbolicLink)
          
    def test_add_ok(self):
        self.assertTrue(self.cfgx.add(self._aConfigFile))
        self.assertTrue(os.path.exists(os.path.join(self._REPO_DIR, self._aConfigFile)), "the file must exist in the repo")
        self.assertTrue(os.path.islink(self._aConfigFile), "the original file must now be a link to the file in the repo")
        
    def test_link_ok(self):
        self.cfgx.add(self._aConfigFile)
        os.remove(self._aConfigFile)
        self.assertTrue(self.cfgx.link(self._aConfigFile), "link() must return True on success")
        self.assertTrue(self.cfgx.link(self._aConfigFile), "even the second time (the link already exists), cfgx.link() should succeed")
    
    def test_link_non_existing(self):
        with self.assertRaises(ConfixError):
            self.cfgx.link('a/non/existing/path')
        with self.assertRaises(ConfixError):
            self.cfgx.link('a/non/existing/path', force=True)
    
    def test_link_file_exists(self):
        self.cfgx.add(self._aConfigFile)
        # self._aConfigFile is a link now -> remove it, create a regular file
        os.remove(self._aConfigFile) 
        open(self._aConfigFile, 'a').close()
        with self.assertRaises(ConfixError):
            self.cfgx.link(self._aConfigFile)
    
    def test_unlink_different_link(self):
        self.cfgx.add(self._aConfigFile)
        os.unlink(self._aConfigFile)
        os.symlink(self._anotherConfigFile, self._aConfigFile)
        with self.assertRaises(ConfixError):
            # a link exists for a file that also exists in the confix repo, but the link points to somewhere else
            self.cfgx.unlink(self._aConfigFile)
     
    def test_unlink_no_symlink(self):
        with self.assertRaises(ConfixError):
            self.cfgx.unlink('a/non/existing/path')
     
    def test_unlink_ok(self):
        self.cfgx.add(self._aConfigFile)
        self.cfgx.unlink(self._aConfigFile)
        self.assertTrue(os.path.exists(self._aConfigFile) 
                        and os.path.isfile(self._aConfigFile) 
                        and not os.path.islink(self._aConfigFile))
     
    def test_unlink_non_existing(self):
        with self.assertRaises(ConfixError):
            self.cfgx.unlink(self._aSymbolicLink) # does not exist in repo
     
    def test_rm_non_existing(self):
        with self.assertRaises(ConfixError):
            self.cfgx.rm('a/non/existing/path')
     
    def test_rm_still_linked(self):
        self.cfgx.add(self._aConfigFile)
        with self.assertRaises(ConfixError):
            self.cfgx.rm(self._aConfigFile)
     
    def test_rm_ok(self):
        self.cfgx.add(self._aConfigFile)
        self.cfgx.unlink(self._aConfigFile)
        self.cfgx.rm(self._aConfigFile)
    
    def test_merge_no_mergeTool(self):
        self.cfgx.add(self._aConfigFile)
        self.cfgx.unlink(self._aConfigFile)
        with self.assertRaises(ConfixError):
            self.cfgx.merge(self._aConfigFile)
    
    def test_merge_invalid_mergeTool(self):    
        self.cfgx.add(self._aConfigFile)
        self.cfgx.unlink(self._aConfigFile)
        self.cfgx.setConfig('MAIN', 'MERGE_TOOL', '/an/invalid/merge/tool')
        with self.assertRaises(ConfixError):
            self.cfgx.merge(self._aConfigFile)
    
    def test_merge_ok(self):
        self.cfgx.add(self._aConfigFile)
        self.cfgx.unlink(self._aConfigFile)
        with open(self._aConfigFile, 'a+') as confFile:
            confFile.write("asdf")
        self.cfgx.setConfig('MAIN', 'MERGE_TOOL', '/usr/bin/ls') # no interactive merge tool for the test, just an executable that exists
        self.cfgx.merge(self._aConfigFile)
     
    def test_fileList(self):
        self.cfgx.add(self._aConfigFile)
        self.cfgx.add(self._anotherConfigFile)
        self.assertEqual(len(self.cfgx.list()), 2)
        os.remove(self._aConfigFile)
        for file in self.cfgx.list():
            filename = file[0]
            isInstalled = file[1]
            if filename == self._aConfigFile:
                self.assertFalse(isInstalled, "must be False because file is not linked")
            elif filename == self._anotherConfigFile:
                self.assertTrue(isInstalled, "must be False because file is linked")
            else:
                assert False

    
if __name__ == '__main__':
    unittest.main()