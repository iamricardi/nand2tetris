# Reads as input a text file containing a Hack assembly program e.g. Prog.asm,
# and produces as output a text file containing the translated Hack machine
# code e.g. Prog.hack.
# The name of the input file is supplied as a command line argument.
#
# This assembler makes the assumption that syntax of the provided assembly
# program is error free.
#
# Usage: python Assembler.py Prog.asm

import sys

A_COMMAND = "A_COMMAND"
C_COMMAND = "C_COMMAND"
L_COMMAND = "L_COMMAND"

predefined_variable_symbols = {
    "SP": 0,
    "LCL": 1,
    "ARG": 2,
    "THIS": 3,
    "THAT": 4,
    "R0": 0,
    "R1": 1,
    "R2": 2,
    "R3": 3,
    "R4": 4,
    "R5": 5,
    "R6": 6,
    "R7": 7,
    "R8": 8,
    "R9": 9,
    "R10": 10,
    "R11": 11,
    "R12": 12,
    "R13": 13,
    "R14": 14,
    "R15": 15,
    "SCREEN": 16384,
    "KBD": 24576
}

def main():
    # Ensure correct number of command line arguments.
    if len(sys.argv) != 2:
        print("Usage: python Assembler.py Prog.asm")
        sys.exit()

    # Ensure command line argument ends in .asm.
    if not sys.argv[1].endswith(".asm"):
        print("Usage: python Assembler.py Prog.asm")
        sys.exit()

    infile_name = sys.argv[1]

    # Prepare to parse the assembly program.
    asmprog = Parser(infile_name)

    # First pass. Go through the entire assembly program, line by line, and
    # build the symbol table without generating any code. As we march through
    # the program's lines, keep a running number recording the ROM address into
    # which the current command will be eventually loaded. This number starts
    # at 0 and is incremented by 1 whenever a C-instruction or an A-instruction
    # is encountered. Each time a pseudocommand (Xxx) is encountered, add a new
    # entry to the symbol table, associating Xxx with the ROM address that will
    # eventually store the next command in the program. This pass results in
    # entering all the program's labels along with their ROM addresses into
    # the symbol table. The program's variables are handled in the second pass.

    # Prepare to built the symbol table.
    symbol_table = SymbolTable()

    rom_address = 0
    while asmprog.has_more_commands():
        asmprog.advance()
        if asmprog.command_type() == L_COMMAND:
            symbol_table.add_entry(asmprog.symbol(), rom_address)
        else:
            rom_address += 1

    # Second pass. Go through the entire assembly program, line by line. Each
    # time a symbolic A-instruction is encountered, namely, @Xxx where Xxx is a
    # symbol and not a number, look up Xxx in the symbol table. If the symbol
    # is found in the table, replace it with its numeric meaning and complete
    # the command's translation. If the symbol is not found in the table, then
    # it must represent a new variable. To handle it, add the pair (Xxx, n) to
    # the symbol table, where n is the next available RAM address, and complete
    # the command's translation. The allocated RAM addresses are consecutive
    # numbers, starting at address 16 (just after the addresses allocated to
    # the predefined symbols).

    # Prepare to translate assembly language to machine language.
    binary_code = Code()

    # Open the output file.
    outfile_name = infile_name.replace(".asm", ".hack")
    try:
        binprog = open(outfile_name, "w")
    except IOError:
        print("Could not open file: " + outfile_name)
        sys.exit()

    # Go to the beginning of the assembly program.
    asmprog.command_index = 0
    asmprog.current_command = None

    ram_address = 16
    while asmprog.has_more_commands():
        asmprog.advance()
        command_type = asmprog.command_type()

        # Skip the pseudocommands.
        if not command_type == L_COMMAND:

            # Generate the binary code.
            if command_type == A_COMMAND:
                symbol = asmprog.symbol()
                if not symbol.isdigit():
                    if symbol_table.contains(symbol):
                        symbol = symbol_table.get_address(symbol)
                    else:
                        if symbol in predefined_variable_symbols:
                            address = predefined_variable_symbols[symbol]
                        else:
                            address = ram_address
                            ram_address += 1
                        symbol_table.add_entry(symbol, address)
                        symbol = symbol_table.get_address(symbol)
                bincode = "0"
                bincode += str(bin(int(symbol)))[2:]
                bincode = bincode.rjust(16, "0")
            else:
                bincode = "111"
                bincode += binary_code.comp(asmprog.comp())
                if asmprog.dest():
                    bincode += binary_code.dest(asmprog.dest())
                else:
                    bincode += "000"
                if asmprog.jump():
                    bincode += binary_code.jump(asmprog.jump())
                else:
                    bincode += "000"

            # Write the binary code to the machine language file.
            binprog.write(bincode + "\n")

    # Close the output file.
    binprog.close()

class Parser:
    def __init__(self, infile_name):
        """
        Opens the input file and gets ready to parse it.
        """
        # Open the input file.
        try:
            f = open(infile_name, "r")
        except IOError:
            print("Could not open file: " + infile_name)
            sys.exit()

        # Store lines of input file in an array.
        lines = f.readlines()

        # Close the input file.
        f.close()

        # Assembly program's commands.
        self.commands = []

        # Strip lines of whitespace and comments.
        # Store lines that have something remaining as commands.
        for line in lines:
            line = "".join(line.split())
            line = line.split("//")[0]
            if len(line):
                self.commands.append(line)

        # Keep track of the current command.
        self.command_index = 0
        self.current_command = None

    def has_more_commands(self):
        """
        Returns True if there are more commands in the input, else False.
        """
        return self.command_index < len(self.commands)

    def advance(self):
        """
        Reads the next command from the input and makes it the current command.
        Should be called only if has_more_commands() is True.
        Initially there is no command.
        """
        self.current_command = self.commands[self.command_index]
        self.command_index += 1

    def command_type(self):
        """
        Returns the type of the current command:
        A_COMMAND for @Xxx where Xxx is either a symbol or a decimal number.
        C_COMMAND for dest=comp;jump.
        L_COMMAND (actually, pseudocommand) for (Xxx) where Xxx is a symbol.
        """
        if self.current_command[0] == "@":
            return A_COMMAND
        elif self.current_command[0] == "(":
            return L_COMMAND
        else:
            return C_COMMAND

    def symbol(self):
        """
        Returns the symbol or decimal Xxx of the current command @Xxx or (Xxx).
        Should be called only when command_type() is A_COMMAND or L_COMMAND.
        """
        if self.command_type() == A_COMMAND:
            return self.current_command[1:]
        else:
            return self.current_command[1:-1]

    def dest(self):
        """
        Returns the dest mnemonic in the current C-command (8 possibilities).
        Should only be called when command_type() is C_COMMAND.
        """
        if "=" in self.current_command:
            return self.current_command.split("=")[0]
        return None

    def comp(self):
        """
        Returns the comp mnemonic in the current C-command (28 possibilities).
        Should only be called when command_type() is C_COMMAND.
        """
        if "=" in self.current_command and ";" in self.current_command:
            tmp = self.current_command.split("=")[1]
            return tmp.split(";")[0]
        elif "=" in self.current_command:
            return self.current_command.split("=")[1]
        else:
            return self.current_command.split(";")[0]

    def jump(self):
        """
        Returns the jump mnemonic in the current C-command (8 possibilities).
        Should only be called when command_type() is C_COMMAND.
        """
        if ";" in self.current_command:
            return self.current_command.split(";")[1]
        return None

class Code():
    def __init__(self):
        self.dest_table = {
            "null": "000",
            "M": "001",
            "D": "010",
            "MD": "011",
            "A": "100",
            "AM": "101",
            "AD": "110",
            "AMD": "111"
        }

        self.comp_table = {
            "0": "0101010",
            "1": "0111111",
            "-1": "0111010",
            "D": "0001100",
            "A": "0110000",
            "!D": "0001101",
            "!A": "0110001",
            "-D": "0001111",
            "-A": "0110011",
            "D+1": "0011111",
            "A+1": "0110111",
            "D-1": "0001110",
            "A-1": "0110010",
            "D+A": "0000010",
            "D-A": "0010011",
            "A-D": "0000111",
            "D&A": "0000000",
            "D|A": "0010101",
            "M": "1110000",
            "!M": "1110001",
            "-M": "1110011",
            "M+1": "1110111",
            "M-1": "1110010",
            "D+M": "1000010",
            "D-M": "1010011",
            "M-D": "1000111",
            "D&M": "1000000",
            "D|M": "1010101"
        }

        self.jump_table = {
            "null": "000",
            "JGT": "001",
            "JEQ": "010",
            "JGE": "011",
            "JLT": "100",
            "JNE": "101",
            "JLE": "110",
            "JMP": "111"
        }

    def dest(self, mnemonic):
        """
        Returns the binary code of the dest mnemonic.
        """
        if mnemonic == None:
            mnemonic = "null"
        return self.dest_table[mnemonic]

    def comp(self, mnemonic):
        """
        Returns the binary code of the comp mnemonic.
        """
        return self.comp_table[mnemonic]

    def jump(self, mnemonic):
        """
        Returns the binary code of the jump mnemonic.
        """
        if mnemonic == None:
            mnemonic = "null"
        return self.jump_table[mnemonic]

class SymbolTable:
    def __init__(self):
        """
        Creates a new empty symbol table.
        """
        self.symbol_table = {}

    def add_entry(self, symbol, address):
        """
        Adds the pair (symbol, address) to the table.
        """
        if not self.contains(symbol):
            self.symbol_table[symbol] = address

    def contains(self, symbol):
        """
        Returns True if the symbol table contains the given symbol, else False.
        """
        return symbol in self.symbol_table

    def get_address(self, symbol):
        """
        Returns the address associated with the symbol.
        """
        if self.contains(symbol):
            return self.symbol_table[symbol]
        return None

main()
