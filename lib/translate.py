#!/usr/bin/python3

import sys
import os
import subprocess
import argparse
import logging
#from translator import Node, Edge, Graph, FSM_Node, FSM_Edge, FSM_Graph
from translator.usr_graph import Node, Edge, Graph
from translator.fsm import FSM_Node, FSM_Edge, FSM_Graph
from translator.rule_tag import FuncParse, Tagging
from translator.TagAssert import *
import logger
from translator.merge import merge

#logger = logger.get_log()
logger = logger.retrieve_log()
logger.debug('--------- TRANSLATION ---------')

rb_loc = subprocess.run(['which', 'rbuild'], stdout=subprocess.PIPE, universal_newlines=True)
if rb_loc.returncode != 0:
    print("RBNotFound: Library not found, you may not have included the rule builder to your PATH")
    sys.exit(1)
rb_loc = rb_loc.stdout.strip()
rb_loc = os.path.dirname(rb_loc)
# Parsing arguments
languages=['c', 'java']
parser = argparse.ArgumentParser(description="Translate")
parser.add_argument('input', nargs='+', help='.mi file for input') # there may be multiple .mi file as input
parser.add_argument('-l', '--lang', help='Target language')
parser.add_argument('-r', '--ref', help='reference mi file, if multiple, concatenate with :')
parser.add_argument('-n', '--name', help='rule name')
args = parser.parse_args()

# ======= User Input validation ========
# input file .mi
logger.debug("User Input Validation")
for i in args.input:
    if not i.endswith('.mi'):
        print("Invalid input file: {}".format(args.input))
        sys.exit(-1)
input_files = args.input

# error name
if not args.name:
    ERROR_NAME="rule"
else:
    ERROR_NAME=args.name

if not args.lang:
    print("Please specify language with -l {c,java}")
    sys.exit(-1)

if args.lang not in languages:
    print("Invalid target language. Choose either 'c' or 'java'")
    sys.exit(-1)
lang = args.lang

if args.ref:
    references = args.ref.split(":")
else:
    references = [os.path.join(rb_loc, 'lib/rt.o.vtable.mi')]

NODE='NODE'
EDGE='EDGE'
TAG='TAG'
ASSERT='ASSERT'
tags = []
def create_usr_graph(f):
    # returning a usr_graph
    logger.debug("Parsing from file %s"%(f))
    fopen = open(f, 'r')
    flines = fopen.readlines()
    content = []
    for f in flines:
        content.append(f.strip())
    gr = Graph()
    for i in content:
        logger.debug("Parsing Content %s"%(i))
        fields = i.split('|')
        if fields[0] == NODE:
            gr.add_nodes(*fields[1:])
        elif fields[0] == EDGE:
            gr.add_edge(*fields[1:])
        elif fields[0] == TAG:
            TagAssert.add_entry_raw(i)
        elif fields[0] == ASSERT:
            TagAssert.add_entry_raw(i) 
        else:
            raise Exception(f"Invalid field, neither node nor edge: {fields[0]}")
    return gr

def create_fsm(g):
    # converting from the usr graph into fsm mode 
    
    logger.debug("Converting the user model to FSM model")
    if len(g.nodes) ==0 :
        return None
    fsm_g = FSM_Graph(g)
    fsm_g.convert()
    return fsm_g

user_graphs = []
for i in input_files:
    try:
        user_graphs.append(create_usr_graph(i))
    except Exception as e:
        logger.debug("Failure in parsing %s"%(i))
        logger.exception("Conversion to user graph model fail") 
        sys.exit(3)

fsm_list = []
for i in user_graphs:
    if i== None:
        continue
    fsm_list.append(create_fsm(i))


#logger.info("Included tags: %s"%tags)  # get all tags
TagAssert.generate(rb_loc)
"""
for i in tags:
    Tagging.add_tags_entry(*i)
Tagging.show_tags()
Tagging.generate(rb_loc)
"""

first = None

if len(fsm_list) > 0:
    first = fsm_list[0]
    if len(fsm_list) > 1:
        first = fsm_list[0]
        for fsm in fsm_list[1:]:
            first = merge(first, fsm)

# copy macros/header to temporary .h first
#read = open('template.h', 'r')
if first != None:
    template_path=os.path.join(rb_loc, 'lib/translator/template.h')
    try:
        read = open(template_path, 'r')
    except Exception as e:
        logger.exception("error in reading template")
        sys.exit(2)

    write = open('rule.h', 'w')
    to_read = read.readlines()
    for r in to_read:
        write.write(r)

# ======== WRITING RULES ===========

def write_transitions(fsm_g):
    for edge in fsm_g.edges:
    # START
        start = edge.start.name
        # FNAME
        if lang=="java":
            # lookup to .mi file 
            reference=args.ref
            #fname = FSM_Graph.find_mangle_f(edge.fname, "org.apache.commons-commons-email.o.vtable.mi")
            #fname= FSM_Graph.find_mangle_f(edge.fname, reference)
            logger.debug("finding mangle of function %s"%(edge.fname))
            fname = FSM_Graph.find_mangle_f_multifile(edge.fname, *references)
        else:
            fname = edge.fname    
        # KEY
        logger.debug("KEY: %s"%(edge.key))
        if edge.key == "this":
            key = "THIS_POINTER"
        elif edge.key == "return":
            key = "GET_RET"     
        else:
            key = "NULL"
        # CONDITION
        logger.debug("Condition: %s"%(edge.condition))
        temp = edge.cond_parse()
        if len(temp) == 0: # no condition
            condition = "1"
        else:
            if temp[0][1] == 'true':
                condition=f"GET_VALUE(GET_ARG({temp[0][0]}))"
            elif temp[0][1] == 'false':
                condition =f"NOT(GET_VALUE(GET_ARG({temp[0][0]})))"
            elif temp[0][1] == 'sensitive':
                condition=f"NOT(IS_SENSITIVE_DATA({temp[0][0]}))"
            elif temp[0][1] == 'not_sensitive':
                condition=f"IS_SENSITIVE_DATA({temp[0][0]})"
        # NEXT STATE
        target=f"\"{edge.target.name}\""
        # ERROR EXIST
        if edge.err == "none":
            error = f"\"\"" 
        else:
            error= f"\"{edge.err}\""
        write.write(f"\t\tADD_TRANSITION(\"{start}\", \"{fname}\", {key}, {condition}, {target}, {error})\n")
      
    logger.debug("Fsm_default_action transitions")
    for e in fsm_g.default_action:
        if isinstance(fsm_g.default_action[e], list):
            for err in fsm_g.default_action[e]:
                if err == "none":
                    err = ""
                write.write("\t\tSET_DEFAULT_ACTION(\"%s\",\"%s\")\n"%(e, err))
        else:
            write.write("\t\tSET_DEFAULT_ACTION(\"%s\",\"%s\")\n"%(e, fsm_g.default_action[e]))

if first != None:

# BEGIN PART (common to all fsm)
    write.write("IMPORT1\nIMPORT2\n")
    write.write(f"CLASS({ERROR_NAME})\n")
    write.write(f"\tSTART_RULE({ERROR_NAME})\n")
    write.write(f"\t\tBUILD_BEGIN(\"{ERROR_NAME}\")\n")
    write.write(f"\t\tNEW_START_STATE\n")
    write.write(f"\t\tNEW_FINAL_STATE\n")
# WRITE TRANSITIONS
#for i in fsm_list:
        #write_transitions(i)
    write_transitions(first)
# END PART (also common to all fsm)
    write.write(f"\t\tBUILD_END(\"{ERROR_NAME}\")\n")
    write.write(f"\t\tRULE_INFO(\"{ERROR_NAME}\", \"DEFAULT\")\n")
    write.write(f"\tEND_RULE\n")
    write.write(f"END_CLASS\n")

# depending on language need to check
if lang == 'c':
    logger.info("Writing into %s.cxx"%(ERROR_NAME))
    if first != None:
        command = f"cpp -P rule.h > {ERROR_NAME}.cxx"
    # for every source file generated from tag/assert, convert it into c
    for f in TagAssert.src_files:
        parts=  f.split('/')
        cmd = f"cpp -P {f} > {parts[-1][:-2]}.c"
        os.popen(cmd)
    #command = ["cpp", "-P", "rule.h", '>', f"{ERROR_NAME}.cxx"]
else:
    logger.info("Writing into %s.java"%(ERROR_NAME))
    if first != None:
        command = f"cpp -P -DLANG_JAVA rule.h > {ERROR_NAME}.java"
    # for every source file generted from tag/assert, convert it into java    
    for f in TagAssert.src_files:
        parts = f.split('/')
        cmd = f"cpp -P -DLANG_JAVA {f} > {parts[-1][:-2]}.java"
        os.popen(cmd) 
if first != None:
    os.popen(command)
    print(f"Check your {ERROR_NAME}.{'cxx' if lang=='c' else 'java'}")
sys.exit(0) # exit with command 0 shows success
