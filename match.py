import csv
import numpy as np
import networkx as nx
from networkx.algorithms.matching import max_weight_matching

FNAME = "partner_data.csv"
TIMES = {"Morning (7am-noon)":0,"Afternoon (noon-6pm)":1, 
"Evening (6pm-midnight)":2, "Night (midnight-7am)":3}
# Index of name in the file
NAME_IND = 1
# Index of email in the file
EMAIL_IND = 2
# Index of contact in the file
CONTACT_IND = 3
# Index of starting time preference in the file
PREF_IND = 4
# List of indices for availability in the file
AVAIL_INDS = range(5,12)
# Index of priority in the file
PRIO_IND = 12
# Maximum difference between student start preferences
PREF_MAX_DIFF = 1
# Maximum difference between student priorities
PRIO_MAX_DIFF = 1

# class used to store data on each student
class Student:
    def __init__(self, name, email, start_pref, priority, available_times, contact):
        self.name = name
        self.start_pref = start_pref
        self.priority = priority
        self.available_times = available_times
        self.contact = contact
        self.email = email
        self.netid = email.split("@")[0]

# imports the student data from the CSV file referenced in FNAME
# outputs a list of Students and a list of corresponding NetIds 
def import_data():
    # open the file and read the data into an array
    students_data = []
    with open(FNAME, newline='') as file:
        reader = csv.reader(file)
        for line in reader:
            students_data.append(line)
        # ignore the first line, because it is a header
        students_data = students_data[1:]
    
    # the array of students we construct
    students = []
    netids = []
    for student_data in students_data:
        # availability array, 1 when available, 0 when not
        avail_arr = np.zeros(28)
        for num, ind in enumerate(AVAIL_INDS):
            # for each day, take the string data and split on commas
            times = student_data[ind].split(",")
            if times == [""]:
                # no availability
                continue
            for time in times:
                time = time.strip()
                # computation for the time in array being referenced
                avail_arr[4*num + TIMES[time]] = 1
        email = student_data[EMAIL_IND]
        netid = email.split("@")[0]
        # constructing the student object and adding it to the array
        students.append(Student(student_data[NAME_IND], email, int(student_data[PREF_IND]),
            int(student_data[PRIO_IND]), avail_arr, student_data[CONTACT_IND]))
        netids.append(netid)
    return students, netids

# builds matrix of scores between students, measuring how suitable they are as partners
def build_suit_matrix(students):
    suit_matrix = np.zeros((len(students),len(students)))
    for i1, s1 in enumerate(students):
        for i2, s2 in enumerate(students):
            # check, for each pair that
            # - the student is not paired with itself
            # - the students start preferences are not too different
            # - the students priorities are not too different
            if (s1 != s2 and 
                np.abs(s1.start_pref - s2.start_pref) <= PREF_MAX_DIFF and
                np.abs(s1.priority - s2.priority) <= PRIO_MAX_DIFF):
                suit_matrix[i1, i2] = np.dot(s1.available_times, s2.available_times)
    return suit_matrix

# builds a (NetworkX) graph of student netids with edges between suitable pairs
def build_graph(netids, suit_matrix, cutoff):
    graph = nx.Graph()
    for index1, netid1 in enumerate(netids):
        for index2, netid2 in enumerate(netids):
            # if student pair is suitable, add them to the graph
            if suit_matrix[index1, index2] >= cutoff:
                if netid1 < netid2:
                    graph.add_edge(netid1,netid2)
    return graph

# matches the students based on graph, and 
# outputs a dictionary matching each index of a Student to the index of their partner
def match_students(students, netids, graph):
    # maps netids to indices of the students/netids list
    netid_to_index = {netid : i for i, netid in enumerate(netids)}
    raw_matching = max_weight_matching(graph, maxcardinality=True)
    matching = {}
    for raw_match in raw_matching:
        s1 = netid_to_index[raw_match[0]]
        s2 = netid_to_index[raw_match[1]]
        matching[s1] = s2
        matching[s2] = s1
    return matching

def print_matching(students, matching):
    matched = set()
    for index in matching:
        name1 = students[index].name
        name2 = students[matching[index]].name
        if name1 <= name2:
            print(name1 + " matched with " + name2)
        matched.add(name1)

    for student in students:
        if student.name not in matched:
            print("\033[91m" + "\n Could not match: " + student.name 
                + ". Make specific arrangements." + "\033[0m")
    

def save_to_csv(filename, matching, students):
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        for student_index in matching:
            student = students[student_index]
            partner = students[matching[student_index]]
            row = [student.email, student.name, partner.email, partner.name, partner.contact]         
            writer.writerow(row)
    
    
if __name__ == "__main__":
    #Get student data and build the suitability matrix
    students, netids = import_data()
    suit_matrix = build_suit_matrix(students)
    # Have the user input the minimum value cutoff for matching of students. 
    user_cutoff = int(input("Desired Cutoff (Enter -1 for maximum full-matching cutoff):"))
    # If the user wants a CSV
    if_csv = input("Would you like this matching to be stored in a CSV if successful (Input true or false):")
    if_csv.lower()
    if if_csv != "true" and if_csv != "false":
        # Make sure the input is valid
        print("Invalid input given")
        exit()
    if_csv = bool(if_csv == 'true')
    output_filename = None
    # Take a filename for the csv
    if if_csv:
        output_filename = input("Filename for CSV:")
    matching = None
    

    if user_cutoff == -1:
        # The "full matching" case
        student_num = len(students)
        # trying full matching
        if student_num % 2 == 1:
            student_num -= 1
            print("\033[93m" + "WARNING: Odd number of students, "+
            "will try to match everyone except one student!" + "\033[0m")
        # Max cutoff should be the min of the maxes across each student
        start_cutoff = int(np.min(np.max(suit_matrix, axis = 0)))
        for cutoff in range(start_cutoff, 0, -1):
            graph = build_graph(netids, suit_matrix, cutoff)
            matching = match_students(students, netids, graph)
            if len(matching) < student_num:
                # Not a maximum matching, go to the next cutoff
                matching = None
                continue
            else:
                # A maximum matching was found
                print_matching(students, matching)
                print("--------------------------------")
                print("Full matching found")
                print("Maximum cutoff: {}".format(cutoff))
                break
        if matching is None:
            # Matching (with cutoff at least 1) isn't possible
            print("Full matching not possible")
    else:
        # The "user-passed-cutoff" case
        # Use the cutoff and find the matching
        graph = build_graph(netids, suit_matrix,user_cutoff)
        matching = match_students(students, netids, graph)
        print_matching(students, matching)
        print("--------------------------------------")
        print("Matching found with {} students matched using cutoff {}".format(len(matching), user_cutoff))
    
    if if_csv and matching is not None:
        save_to_csv(output_filename, matching, students)
