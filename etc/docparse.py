#!/usr/bin/env python
#Parses a markdown file (first command line argument)
#containing a table with the header whose header starts with:
#| Name | RW | Command Code

def extract_table(file_str):
	"""Extract the command table from the text of
	   specification.md. Returns a list of dictionaries with the following
	   members:
	     "name"     : str, name of command
	     "rw"       : str, contains r is command can be read, w if command can be written, - if neither
	     "code"     : int, command code (0-127)
	     "argument" : list( #list of 0 or more tuples, each with the following structure:
	       tuple(format code:str, #command format code, u8, i16, etc, or * to indicate a
	                              #a variable number of bytes controlled by the previous argument.
	             name:str))
	     "default"  : list of default values of arguments, as strings
	     "notes"    : str, notes on command."""
	s = file_str.find("\n| Name | RW | Command Code")
	s+=1 #Skip over first newline
	e = file_str[s:].find("\n\n")
	if e < s:
		table_str = file_str[s:]
	else:
		table_str = file_str[s:s + e]
	commands = []
	for l in table_str.split("\n"):
		if len(l) == 0: continue
		if l[0] == "|":
			l = l[1:]
		col = [c.strip() for c in l.split("|")]
		if col[0][0:3] == "---": continue
		if col[0] == "Name": continue
		name = col[0]
		rw = col[1].lower()
		code = int(col[2], 0)
		notes = col[5]
		argument = []
		for a in [c.strip() for c in col[3].split(",")]:
			a = a.split(" ")
			if len(a) == 2:
				argument.append((a[0], a[1]))
		default = []
		if len(argument) > 0:
			for d in [c.strip() for c in col[5].split(",")]:
				default.append(d)
		commands.append({
			"name" : name,
			"rw"   : rw,
			"code" : code,
			"argument" : argument,
			"default"  : default,
			"notes" : notes})
	return commands

def format_code_to_cstdint(fmt_name):
	"""Convert a format code (i8, u16, *, etc) to a c standard int (int8_t, uint16_t, uint8_t *)."""
	if fmt_name == "*":
		return "uint8_t *"
	elif fmt_name[0] == "i":
		return "int%s_t"%fmt_name[1:]
	elif fmt_name[0] == "u":
		return "uint%s_t"%fmt_name[1:]
	else:
		raise ValueError("Unknown format code \"%s\""%fmt_name)

def format_code_size(fmt_name):
	"""Return the number of bytes required for a type with the given format code."""
	if fmt_name == "*":
		return 255
	else:
		return int(fmt_name[1:])/8
	
def send_prototype(cmd_dict):
	"""Given a command dictionary (from extract_table), return a function that constructs
	   a packet of that type. The function relies on the following function:
	     send(uint8_t *data, uint16_t count) - send the given packet across the radio link.
	                                           The send() function must add a start byte and 
	                                           escape start and escape characters where necessary.
	     pack*(void *data, uint16_t pos) - pack the given value (where * = 8, 16, 32, or 64 bits)
	                                         into the given buffer position in a little-endian format.
	     memcpy(void *dest, void *src, uint16_t count) - copy bytes"""
	cmd = cmd_dict
	#Prototype
	proto = "void "
	proto += "send_" + cmd["name"].lower().replace(" ", "_") + "("
	for a in cmd["argument"]:
		proto += format_code_to_cstdint(a[0]) + " " + a[1] + ", "
	proto = proto[0:-2] #Remove last commma 
	proto += "){\n"
	
	#Packet stuffing
	body = ""
	totalsize = 0 #current byte in packet buffer
	prev_a = None
	for a in cmd["argument"]:
		if a[0] == "*":
			if prev_a == None:
				raise ValueError("In command %s, variable-length argument used before length controlling argument.")
			body += "\tmemcpy(buf + b, %s, %s);\n"%(a[1], prev_a[1])
			body += "\tb += %s;\n"%prev_a[1]
			totalsize += 255
		else:
			s = format_code_size(a[0])
			body += "\tpack%d(&%s, buf + b);\n"%(s*8, a[1])
			body += "\tb += %d;\n"%s
			totalsize += s
		prev_a = a
		
	#Send command
	send = "\tsend(buf, b);\n}\n"
		
	#Declarations
	declarations = "\tuint16_t b = 0;\n\tuint8_t buf[%d];\n"%totalsize
	
	return proto + declarations + body + send

if __name__ == "__main__":
	import sys
	with open(sys.argv[1], "r") as f:
		cmds = extract_table(f.read())
		for c in cmds:
			print send_prototype(c)
		








