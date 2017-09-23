#!/usr/bin/env python

from __future__ import absolute_import, division, print_function, unicode_literals

import os
import sys
import inspect
import logging
import requests

RSERVER = "https://<racetrack-server>";
TESTTYPES = ("BATS","Smoke","Regression", "DBT", "Unit", "Performance")
LANGUAGES = ("English","Japanese","French", "Italian", "German", "Spanish", "Portuguese", "Chinese", "Korean")
RESULTTYPES = ("PASS","FAIL","RUNNING", "CONFIG", "SCRIPT", "PRODUCT", "RERUNPASS", "UNSUPPORTED")
VERIFYRESULTS = ("TRUE","FALSE")

class RaceTrack:
    def __init__(self):
        self.testSetID = None
        self.testCaseID = None
        self.testCaseResult = None
        self.goodConnection = True
        
        try:
            response = requests.get(url=RSERVER, timeout=5)
        except Exception:
            self.goodConnection = False
        
    def post(self, webServiceMethod, params, files=None):
        headers = {"charset": "UTF-8"}
        #if files:
        #    headers = {'content-type': 'multipart/form-data'}
            
        url = "%s/%s" % (RSERVER, webServiceMethod)
        response = None
        try:
            if files:
                response = requests.post(url, files=files, data=params, headers=headers)
            else:
                response = requests.post(url, data=params, headers=headers)
        except Exception:
            logging.error("Error: post request faild")
        return response

    def testSetBegin(self, BuildID=None, User=None, Product=None, Description=None, HostOS=None, 
                     ServerBuildID='',
                     Branch='',
                     BuildType='',
                     TestType='Regression',
                     Language='English', config={}):
        '''
             * Returns a new test set ID on success or None on failure.
              Param          Required?   Description
              BuildID        Yes         The build number that is being tested
              User           Yes         The user running the test
              Product        Yes         The name of the product under test
              Description    Yes         A description of this test run
              HostOS         Yes         The Host OS
              ServerBuildID  No          The build number of the "server" product
              Branch         No          The branch which generated the build
              BuildType      No          The type of build under test
              TestType       No          default Regression
              Language       No          default English 
        '''
        params = config
        if params:
            for k in ["BuildID", "User", "Product", "Description", "HostOS"]:
                if not params.get(k):
                    logging.error('testSetBegin: invalid config, lack param: ' + k)
        else:
            if (Language  == None) or (Language not in LANGUAGES):
                logging.error("testSetBegin: Specified language is invalid - %s", Language)
                return None
            if (TestType == None) or (TestType not in TESTTYPES):
                logging.error("testSetBegin: Specified test type is invalid - %s", TestType)
                return None

            frame = inspect.currentframe()
            args, _, _, values = inspect.getargvalues(frame)
            for i in args:
                if values[i] == None:
                    continue
                if i in ['self', 'config']:
                    continue
                
                params[i] = values[i]
        r = self.post("TestSetBegin.php", params)
        if not r:
            return None
            
        self.testSetID = int(r.text)
        return r.text
        
    def testSetData(self, Name, Value):
        if not self.testSetID:
            logging.error("testSetData called but there is no active test set.")
            return None
        params = {'ResultSetID': self.testSetID} 
        frame = inspect.currentframe()
        args, _, _, values = inspect.getargvalues(frame)
        for i in args:
            if values[i] == None:
                continue
            if i in ['self', 'config']:
                continue
            params[i] = values[i]
        
        r = self.post("TestSetData.php", params)
        if not r:
            return None
        return r
    
    def testSetEnd(self):
        '''
        * testSetEnd - End the test set

          Param          Required?           Description
          testSetID             No          The test set/run that is being completed.
        '''
        return self.post("TestSetEnd.php", {"ID":str(self.testSetID)})
        
    def testCaseBegin(self, Name=None, Feature=None,
                      Description='',
                      MachineName='',
                      TCMSID='',
                      InputLanguage='', config={}):
        '''
        * testCaseBegin - Start a new test case

          Param          Required?   Description
          Name           Yes         The name of the test case
          Feature        Yes         The feature that is being tested
          Description    No          A description of this test case
          MachineName    No          The host that the test is running against
          TCMSID         No          A comma-separated Testlink (TCMSID) ID's.
          InputLanguage  No          abbreviation for the language used eg 'EN'
          ResultSetID    No          The test set/run that is being completed. (We will use the testSetID which is created in testSetBegin)
        '''  
        if not self.testSetID:
            logging.error("testCaseBegin called but there is no active test set.")
            return None
        
        case_params = {}
        if config:
            for k in ["Name", "Feature"]:
                if not config.get(k):
                    logging.error('testSetBegin: invalid config, lack param: ' + k)

            for k in ['Name', 'Feature', 'Description', 'MachineName', 'TCMSID', 'InputLanguage',
                      'Type', 'TestPriority', 'Method', 'Remark', 'Validation']:
                case_params[k] = config.get(k, '')
        else:
            frame = inspect.currentframe()
            args, _, _, values = inspect.getargvalues(frame)
            for i in args:
                if values[i] == None:
                    continue
                if i in ['self', 'config']:
                    continue
                case_params[i] = values[i]

        case_params['ResultSetID'] = self.testSetID
        r = self.post("TestCaseBegin.php", case_params)
        if not r:
            return None
            
        self.testCaseID = int(r.text)
        self.testCaseResult = "PASS";
        return r.text
        
    def testCaseEnd(self, Result=None):
        '''
        * testCaseEnd - End a test case
          Param          Required?   Description
          Result         No          The result of the test. Enum of 'PASS',
                                     'FAIL', 'RUNNING','CONFIG','SCRIPT',
                                     'PRODUCT','RERUNPASS', or 'UNSUPPORTED'
        '''
        if not Result:
            Result = self.testCaseResult

        if Result not in RESULTTYPES:
            logging.error("testCaseEnd: Specified test result is invalid. - %s", Result)
            return None

        r = self.post("TestCaseEnd.php", {"ID":self.testCaseID, "Result":Result})
        if not r:
            return None
        
        self.testCaseID = None;
        self.testCaseResult = None;
        
        return r
        
    def testCaseComment(self, comment):
        if not comment:
            logging.error("testCaseComment: comment not valid.")
            return None
        if not self.testCaseID:
            logging.error("testCaseComment: there is no active test case.")
            return None

        r = self.post("TestCaseComment.php", {"ResultID":self.testCaseID, "Description":comment})
        return r
        
    def TestCaseWarning(self, warning):
        if not warning:
            logging.error("TestCaseWarning: warning not valid.")
            return None
        if not self.testCaseID:
            logging.error("TestCaseWarning: there is no active test case.")
            return None

        r = self.post("TestCaseWarning.php", {"ResultID":self.testCaseID, "Description":warning})
        return r
        
    def uploadScreenshot(self, Description, Screenshot):
        '''
        * uploadScreenshot - upload a screenshot

          Param          Required?   Description
          Description    Yes         The comment
          Screenshot     Yes         The screenshot location including file name and path
        '''
        if not self.testCaseID:
            logging.error("uploadScreenshot: uploadScreenshot called but there is no active test case.")
            return None
        if not os.path.isfile(Screenshot):
            logging.error("uploadScreenshot: Screenshot is invalid.")
            return None
        params = {"Description": Description,
                  "ResultID": self.testCaseID}
                  
        files = None
        if Screenshot:
            if os.path.isfile(Screenshot):
                files = {'Screenshot': (os.path.basename(Screenshot), open(Screenshot, 'rb'))}
                
        r = self.post("TestCaseScreenshot.php", params, files=files)
        return r

    def uploadLog(self, Description, Log):
        '''
        * uploadLog - upload a log

          Param          Required?   Description
          Description    Yes         The comment
          Log            Yes         The log location including file name and path
        '''
        if not self.testCaseID:
            logging.error("uploadLog: uploadLog called but there is no active test case.")
            return None
        if not os.path.isfile(Log):
            logging.error("uploadLog: Log is invalid.")
            return None
        params = {"Description": Description,
                  "ResultID": self.testCaseID}
        files = None
        if Log:
            if os.path.isfile(Log):
                files = {'Log': (os.path.basename(Log), open(Log, 'rb'))}

        r = self.post("TestCaseLog.php", params, files=files)
        
    def verify(self, Description, Actual, Expected, Screenshot):
        '''
        * Param                  Required?   Description
        * @param Description    Yes         The comment
        * @param Actual            Yes         The actual value. (any string)
        * @param Expected        Yes         The expected value. (any string)
        * @param Screenshot        No          A screenshot associated with the (failed) verification
        '''
        if not self.testCaseID:
            logging.error("verify: verify called but there is no active test case.")
            return None
        
        if (not Actual) or (not Expected):
            logging.error("verify: invalid Actual or invalid Expected .")
            return None
        
        testVerify = 'TRUE'
        if Actual != Expected:
            testVerify = "FALSE";
            self.testCaseResult = 'FAIL'
        
        params = {"ResultID": self.testCaseID,
                  "Description": Description,
                  "Actual": Actual,
                  "Expected": Expected,
                  "Result": testVerify}
        files = None
        if Screenshot:
            if os.path.isfile(Screenshot):
                files = {'Screenshot': (os.path.basename(Screenshot), open(Screenshot, 'rb'))}
        
        r = self.post("TestCaseVerification.php", params, files=files)
        return r
        
if __name__ == "__main__":
    if len(sys.argv) == 2:
        if sys.argv[1] == 'test':
            #log_file = r'D:\projects\racetrackpy\t.log'
            #png_file = r'D:\projects\racetrackpy\t.png'
            
            t = RaceTrack()
            r = t.testSetBegin("11101", "test", "G11N_vCAC", "For Test", "Win 7")
            if r: print(r)
            r = t.testCaseBegin("case1", "feature1", "For test:case1")
            if r: print(r)
            r = t.testCaseComment("this is a comment.")
            if r: print("testCaseComment: ", r.text)
            #r = t.uploadScreenshot("Screenshot Test", png_file)
            #if r: print("uploadScreenshot: ", r.text)
            #r = t.uploadLog("Upload Log test", log_file)
            #if r: print("uploadLog: ", r.text)
            r = t.verify("des test1", "???????", "???????", None);
            if r: print("verify: ", r.text)
            #r = t.verify("des test2", "???????", "b", png_file);
            #if r: print("verify: ", r.text)
            r = t.testCaseEnd();
            if r: print("testCaseEnd: ", r.text)
            r = t.testSetEnd();
            if r: print("testSetEnd: ", r.text)
