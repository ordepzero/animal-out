#!/usr/local/bin/python2.7
# encoding: utf-8
'''
src.animal_out -- Machine Learning Algorithm

@author:     Laercio, Pedro and Lucca
@copyright:  2016 ICMC. All rights reserved.
@license:    license
@contact:    leoabubauru@hotmail.com
@deffield    updated: Updated
'''

import sys
import os
import time
import pandas as datafile
import matplotlib.pyplot as plt
from matplotlib import style
style.use("ggplot")

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_score
from sklearn.preprocessing import LabelEncoder, normalize


###############################################################################
#                           SOME PARAMETERS
###############################################################################

# Global variables
verbose = 0
nanfill = False
nominal2numeric = False
norm_data = False
remove_corr = False
run_alg = False
tunning_par = False
choose_alg = False
new_train_file = ""

# TODO: Remover a lista de atributos abaixo apos implementar a 
# rotina de pre-processamento

# Target attribute
target_att = ["target"]

# ID attribute
id_att = ["ID"]

# Nominal attributes drop out list
nominal_att_droplist = ["v3", "v22", "v24", "v30", "v31", "v47", "v52", "v56", \
                        "v66", "v71", "v74", "v75", "v79", "v91", "v107", \
                        "v110", "v112", "v113", "v125"]

# No-distribution attributes drop out list
nodist_att_droplist = ["v23", "v38"]

# Const-distribution attributes drop out list
constdist_att_droplist = []

# Duplicated attributes drop out list. Leaving only one of them.
double_att_droplist = []

# Attributes with correlation > 95% drop out list
correlation95_att_droplist = ["v46", "v53", "v54", "v60", "v63", "v76", "v83", \
                              "v89", "v95", "v96", "v100","v105", "v106","v114",\
                              "v115","v116","v118","v121",]

# Others attributes drop out list
others_att_droplist = []


###############################################################################
#                       AGE CONVERSION FUNCTION
###############################################################################
def age_to_days(item):
    # convert item to list if it is one string
    if type(item) is str:
        item = [item]
    ages_in_days = datafile.np.zeros(len(item))
    for i in range(len(item)):
        # check if item[i] is str
        if type(item[i]) is str:
            if 'day' in item[i]:
                ages_in_days[i] = int(item[i].split(' ')[0])
            if 'week' in item[i]:
                ages_in_days[i] = int(item[i].split(' ')[0])*7
            if 'month' in item[i]:
                ages_in_days[i] = int(item[i].split(' ')[0])*30
            if 'year' in item[i]:
                ages_in_days[i] = int(item[i].split(' ')[0])*365    
        else:
            # item[i] is not a string but a nan
            ages_in_days[i] = 0
    return ages_in_days


###############################################################################
#                       GET SEX FUNCTION
###############################################################################
def get_sex(x):
    x = str(x)
    if x.find('Male')   >= 0: return 'male'
    if x.find('Female') >= 0: return 'female'
    return 'unknown'


###############################################################################
#                       GET NEUTERED FUNCTION
###############################################################################
def get_neutered(x):
    x = str(x)
    if x.find('Spayed')   >= 0: return 'neutered'
    if x.find('Neutered') >= 0: return 'neutered'
    if x.find('Intact')   >= 0: return 'intact'
    return 'unknown'
        
        
###############################################################################
#                       GET DATE FUNCTION
###############################################################################
def get_date_info(date_time):
    date_time = str(date_time)
    return date_time.split(" ")[0]
        
       
###############################################################################
#                       GET TIME FUNCTION
###############################################################################
def get_time_info(date_time):
    date_time = str(date_time)
    return date_time.split(" ")[1]
       
        
###############################################################################
#                    BUILD A NEW TRAIN/TEST FILE FUNCTION
# Each task print some info and calculates spent time by itself.
# Then split some data as the original datafile has mixed info in it.
###############################################################################
def get_new_file(filename):
    global verbose
    
    # First of all we need open/read the datafile
    if verbose > 0:
        print_progress("Opening %s file to rebuild it." % os.path.abspath(filename))
        start_time = time.clock()
    csv_file = datafile.read_csv(filename)
    if verbose > 0:
        print("--> %8.3f seconds" % (time.clock() - start_time))
        
    # One of the files has a different column ID name. Fix it so that
    # both train and test have the same column name for ID    
    if "AnimalID" in csv_file.columns:
        csv_file=csv_file.rename(columns = {"AnimalID":"ID"})


    # Then we convert 'AgeuponOutcome' to unit 'days'
    if verbose > 0:
        print_progress("Converting age to days...")
        start_time = time.clock()
    feature_values = csv_file["AgeuponOutcome"].values
    csv_file["DaysUponOutcome"] = age_to_days(feature_values)
    csv_file.drop("AgeuponOutcome", axis=1, inplace = True)
    if verbose > 0:
        print("--> %8.3f seconds" % (time.clock() - start_time))

    
    # Split sex and neutered info in two new columns
    if verbose > 0:
        print_progress("Splitting sex and neutered info...")
        start_time = time.clock()
    csv_file["Sex"] = csv_file["SexuponOutcome"].apply(get_sex)
    csv_file["Neutered"] = csv_file["SexuponOutcome"].apply(get_neutered)
    csv_file.drop("SexuponOutcome", axis=1, inplace = True)
    if verbose > 0:
        print("--> %8.3f seconds" % (time.clock() - start_time))


    # Date/time is also splited in two new columns
    if verbose > 0:
        print_progress("Splitting date and time info...")
        start_time = time.clock()
    csv_file["Date"] = csv_file["DateTime"].apply(get_date_info)
    csv_file["Time"] = csv_file["DateTime"].apply(get_time_info)
    csv_file.drop("DateTime", axis=1, inplace = True)
    if verbose > 0:
        print("--> %8.3f seconds" % (time.clock() - start_time))


    # Generates a new column with boolean info 'isMix' for breed
    if verbose > 0:
        print_progress("Detecting if is a Mix breed...")
        start_time = time.clock()
    csv_file["isMix"] = csv_file["Breed"].apply(lambda x: "Mix" in x)
    if verbose > 0:
        print("--> %8.3f seconds" % (time.clock() - start_time))


    # Breed must be handled as it has many different types. So we
    # take only the first breed before '/' and remove 'Mix'
    if verbose > 0:
        print_progress("Getting first breed and removing Mix...")
        start_time = time.clock()
    csv_file["singleBreed"] = csv_file["Breed"].apply(lambda x: x.split("/")[0])
    csv_file["singleBreed"] = csv_file["singleBreed"].apply(lambda x: x.split(" Mix")[0])
    csv_file.drop("Breed", axis=1, inplace = True)
    if verbose > 0:
        print("--> %8.3f seconds" % (time.clock() - start_time))

    
    # Also for colors we split them and take only the first one
    if verbose > 0:
        print_progress("Getting first color...")
        start_time = time.clock()
    csv_file["singleColor"] = csv_file["Color"].apply(lambda x: x.split("/")[0])
    if verbose > 0:
        print("--> %8.3f seconds" % (time.clock() - start_time))
        
        
    # Count colors in each animal
    if verbose > 0:
        print_progress("Counting color for each animal ...")
        start_time = time.clock()
    csv_file["nbrofColors"] = csv_file["Color"].apply(lambda x: len((x.split("/"))))
    csv_file.drop("Color", axis=1, inplace = True)
    if verbose > 0:
        print("--> %8.3f seconds" % (time.clock() - start_time))
        
                            
    # Create a atribute with info if the animal has a name
    if verbose > 0:
        print_progress("Has the animal a name?")
        start_time = time.clock()
    csv_file["hasName"] = csv_file["Name"].apply(lambda x: type(x) is str)
    csv_file.drop("Name", axis=1, inplace = True)
    if verbose > 0:
        print("--> %8.3f seconds" % (time.clock() - start_time))
        
        
    # Now we have a new datafile
    return csv_file    
   
   
###############################################################################
#                           PRE_PROCESS FUNCTION
###############################################################################
def pre_process(filename):
    global verbose, nanfill, nominal2numeric, norm_data, remove_corr
 
 
#     if (nominal2numeric == True):
#         if verbose > 0:
#             print_progress("Converting nominal to numeric data...")
#             start_time = time.clock()
#         to_number = LabelEncoder()
#         csv_file["v3"  ] = to_number.fit_transform(csv_file.v3)
#         csv_file["v22" ] = to_number.fit_transform(csv_file.v22)
#         csv_file["v24" ] = to_number.fit_transform(csv_file.v24)
#         csv_file["v30" ] = to_number.fit_transform(csv_file.v30)
#         csv_file["v31" ] = to_number.fit_transform(csv_file.v31)
#         csv_file["v47" ] = to_number.fit_transform(csv_file.v47)
#         csv_file["v52" ] = to_number.fit_transform(csv_file.v52)
#         csv_file["v56" ] = to_number.fit_transform(csv_file.v56)
#         csv_file["v66" ] = to_number.fit_transform(csv_file.v66)
#         csv_file["v71" ] = to_number.fit_transform(csv_file.v71)
#         csv_file["v74" ] = to_number.fit_transform(csv_file.v74)
#         csv_file["v75" ] = to_number.fit_transform(csv_file.v75)
#         csv_file["v79" ] = to_number.fit_transform(csv_file.v79)
#         csv_file["v91" ] = to_number.fit_transform(csv_file.v91)
#         csv_file["v107"] = to_number.fit_transform(csv_file.v107)
#         csv_file["v110"] = to_number.fit_transform(csv_file.v110)
#         csv_file["v112"] = to_number.fit_transform(csv_file.v112)
#         csv_file["v113"] = to_number.fit_transform(csv_file.v113)
#         csv_file["v125"] = to_number.fit_transform(csv_file.v125)
#         if verbose > 0:
#             print("--> %8.3f seconds" % (time.clock() - start_time))
# 
# 
#     if (nominal2numeric == False):        
#         if verbose > 0:
#             print_progress("Removing nominal attributes...")
#             start_time = time.clock()
#         csv_file.drop(nominal_att_droplist, axis=1, inplace = True)
#         if verbose > 0:
#             print("--> %8.3f seconds" % (time.clock() - start_time))
#         
#     if (remove_corr == True):
#         if verbose > 0:
#             print_progress("Removing attributes with correlation >= 95% ...")
#             start_time = time.clock()
#         csv_file.drop(correlation95_att_droplist, axis=1, inplace = True)
#         if verbose > 0:
#             print("--> %8.3f seconds" % (time.clock() - start_time))
#    
#     # Only remove lines for training. Test data must be treated with all data. 
#     if verbose > 0:
#         start_time = time.clock()
#     if (nanfill == True):
#         if verbose > 0:
#             print_progress("Filliing NAN with -1...")
#         processed_file = csv_file.fillna(-1)
#     else:
#         if verbose > 0:
#             print_progress("Removing NAN from data...")
#         processed_file = csv_file.dropna()
#     if verbose > 0:
#         print("--> %8.3f seconds" % (time.clock() - start_time))
# 
#     # processed_file still keep 'ID' and, maybe, 'target' attributes.
#     # Let's remove them!
#     id_data = processed_file["ID"].values
#     if "target" in csv_file.columns:
#         target_data    = processed_file["target"].values
#         processed_file = processed_file.drop(target_att + id_att, axis=1)
#         if (norm_data == True):
#             if verbose > 0:
#                 print_progress("Normalizing data...")
#                 start_time = time.clock()
#             processed_file = normalize(processed_file, norm='l2', axis=1, copy=False)
#             if verbose > 0:
#                 print("--> %8.3f seconds" % (time.clock() - start_time))
#         return processed_file, id_data, target_data
#     else:
#         processed_file = processed_file.drop(id_att, axis=1)
#         if (norm_data == True):
#             if verbose > 0:
#                 print_progress("Normalizing data...")
#                 start_time = time.clock()
#             processed_file = normalize(processed_file, norm='l2', axis=1, copy=False)
#             if verbose > 0:
#                 print("--> %8.3f seconds" % (time.clock() - start_time))
        # TODO Remover as atribuicoes abaixo
    processed_file = filename.dropna()
    id_data = processed_file["ID"].values
    return processed_file, id_data
        
        
###############################################################################
#                           RUN_ALGORITHM FUNCTION
###############################################################################
def tunning_parameters():
    parameter = 0


###############################################################################
#                       CHOOSE THE BEST ALGORITHM FUNCTION
###############################################################################
def choose_best_algorithm():
    alg_chosen = ''

    return alg_chosen

###############################################################################
#                           RUN_ALGORITHM FUNCTION
###############################################################################
def run_algorithm(best_alg, train_file, test_file, target_data, train_sample_size):
#     global verbose
#     perc = 0.1 # Percentage to build a training/test files
#     
#     if verbose > 0:
#         print_progress("Create the random forest object for fitting.")
#         start_time = time.clock()
#     # random_state=1000 is a magic number. See answer by cacol89 in this question: 
#     # http://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html    
#     classif = RandomForestClassifier(n_estimators = 200, n_jobs = -1, \
#                                      max_features=None, random_state=1000, \
#                                      class_weight={1:0.7612, 0:0.2388})
#     if verbose > 0:
#         print("--> %8.3f seconds" % (time.clock() - start_time))
# 
# 
#     if verbose > 0:
#         print_progress("Creating training data for fitting...")
#         start_time = time.clock()
#     # We need a subset of a known data in order to fit the classifier
#     # and calculate its score.
#     train_fit_file  = train_file[:train_sample_size]
#     fit_target_data = target_data[:train_sample_size]
#     if verbose > 0:
#         print("--> %8.3f seconds" % (time.clock() - start_time))
# 
#     if verbose > 0:
#         print_progress("Performing fitting...")
#         start_time = time.clock()
#     fit_result = classif.fit(train_fit_file, fit_target_data)
#     if verbose > 0:
#         print("--> %8.3f seconds" % (time.clock() - start_time))
#     
#     
#     if verbose > 0:
#         print_progress("Performing prediction on training data...")
#         start_time = time.clock()
#     # As we took a percentage of data to fit the classifier, now we use 
#     # 100% - perc for training data
#     train_file  = train_file [int(len(fit_target_data)):int(len(fit_target_data))+int(len(fit_target_data) * perc)]
#     target_data = target_data[int(len(fit_target_data)):int(len(fit_target_data))+int(len(fit_target_data) * perc)]
#     prediction  = fit_result.predict(train_file)    
#     if verbose > 0:
#         print("--> %8.3f seconds" % (time.clock() - start_time))
# 
# 
#     if verbose > 0:
#         print_progress("Calculating training score...")
#         start_time = time.clock()
#     training_score = precision_score(target_data, prediction)
#     if verbose > 0:
#         print("--> %8.3f seconds" % (time.clock() - start_time))
#     
# 
#     if verbose > 0:
#         print_progress("Performing prediction on test data...")
#         start_time = time.clock()
#     prediction  = fit_result.predict(test_file)    
#     pred_prob   = fit_result.predict_proba(test_file)
#     if verbose > 0:
#         print("--> %8.3f seconds" % (time.clock() - start_time))
# 
# 
    # TODO Remover as atribuicoes abaixo
    training_score = 0.0
    pred_prob = 0.0
    return training_score, pred_prob


###############################################################################
#                           SHOW_RESULTS FUNCTION
###############################################################################
def print_progress(msg):
# line length
# 1      10        20        30        40        50        60        70       80
# 345678901234567890123456789012345678901234567890123456789012345678901234567890
    msglen = len(msg)
    fillspaces = 50 - msglen 
    msg = msg + fillspaces * ' '
    print ("%s" % msg),    


###############################################################################
#                           SHOW_RESULTS FUNCTION
###############################################################################
def print_results(pred_prob, training_score, id_test, out_filename, totaltime):
    global verbose

    print ("Training accuracy: %.2f" % (training_score * 100.0))    

    if verbose > 0:
        start_time = time.clock()
        print_progress("Writing output file...")
#     datafile.DataFrame({"ID": id_test, "PredictedProb": pred_prob[:,1]}).\
#                         to_csv(out_filename, index=False)
    if verbose > 0:
        print("--> %8.3f seconds" % (time.clock() - start_time))
        print("Total execution time: %8.3f seconds" % (time.clock() - totaltime))
    if verbose > 0:
        print("Done!")


#######################################################################
#       ALTERNATIVE PRE PROCESS 
#######################################################################
def pre_process_shelter(csv_file):
    to_number = LabelEncoder()
    csv_file["AnimalType"] = to_number.fit_transform(csv_file['AnimalType'])
    csv_file["OutcomeType"] = to_number.fit_transform(csv_file['OutcomeType'])
    csv_file["Sex"] = to_number.fit_transform(csv_file['Sex'])
    csv_file["Neutered"] = to_number.fit_transform(csv_file['Neutered'])
    csv_file["isMix"] = to_number.fit_transform(csv_file['isMix'])
    csv_file["hasName"] = to_number.fit_transform(csv_file['hasName'])

    return csv_file
    
#######################################################################
#       ALTERNATIVE MAIN
#######################################################################
def alternative_main(argv=None):
    global new_train_file
    
    actual_directory = os.path.dirname(os.path.abspath(__file__))
    
    os.chdir("..")
    actual_directory = os.path.abspath(os.curdir)
    
    train_file = actual_directory+'\\data\\train.csv';

    #records = datafile.read_csv(train_file)
    
    #print (records['OutcomeType'])
    
    new_train_file = get_new_file(train_file)
    new_train_file = pre_process_shelter(new_train_file)
    
###############################################################################
#                               MAIN FUNCTION
###############################################################################
def main(argv=None): # IGNORE:C0111
    global verbose, nanfill, nominal2numeric, norm_data, remove_corr, run_alg, \
           choose_alg, tunning_par

    total_time = time.clock()

    try:
        # Parser for command line arguments
        parser = ArgumentParser()
        parser.add_argument("-c", dest="remove_cor", default=False, action="store_true", help="remove attributes with correlation >= 95% between each other")
        parser.add_argument("-m", dest="norm_data" , default=False, action="store_true", help="norm numeric data")
        parser.add_argument("-n", dest="nanfill"   , default=False, action="store_true", help="fills nan values with -1")
        parser.add_argument("-s", dest="size_tr"   , default=1000 ,                      help="sample size for training")
        parser.add_argument("-v", dest="verbose"   , default=0    , action="count",      help="shows script execution steps")
        parser.add_argument("-x", dest="nom2num"   , default=False, action="store_true", help="convert nominal attributes to numerical")

        # Process arguments
        args           = parser.parse_args()
        verbose        = args.verbose
        train_filename = "./data/train.csv"
        test_filename  = "./data/test.csv"
        out_filename   = "./out/result.csv"
        nanfill        = args.nanfill 
        nominal2numeric= args.nom2num
        norm_data      = args.norm_data
        remove_corr    = args.remove_cor
        sample_size_tr = int(args.size_tr)

        if verbose > 0:
            print("Verbose mode: ON")

        if (train_filename and test_filename and out_filename) and \
           (train_filename == test_filename) or (train_filename == out_filename) or \
           (test_filename == out_filename):
            print("ERROR: Input and output filenames must be unique!")
        
        
        # Handle input files as they have mixed info in the attributes
        new_train_file = get_new_file(train_filename)
        new_test_file  = get_new_file(test_filename)
        
        # Pre-process the data
        train_file, target_data = pre_process(new_train_file)
        test_file, test_id_data = pre_process(new_test_file)
        
        # Run cross-validation to tune parameters for the algorithms
        tunning_parameters()
        
        # Run cross-validation to choose the best algorithm for this problem
        best_alg = choose_best_algorithm()
        
        # Run the algorithm chosen
        train_score, pred_prob = run_algorithm(best_alg, \
                                               train_file, \
                                               test_file, \
                                               target_data, \
                                               sample_size_tr)
        
        # Print the results and save a file with the probabilities
        print_results(pred_prob, train_score, test_id_data, \
                      out_filename, total_time)        
        
        # Ends application
        return 0
    
    
    # Handle errors
    except Exception as e:
        raise(e)
        return 2


# Application start up
if __name__ == "__main__":
    #sys.exit(main())
    sys.exit(alternative_main())