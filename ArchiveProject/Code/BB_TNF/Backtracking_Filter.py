#! /usr/bin/env python
#
# Backtracking_Filter.py
#
"""
Filters out machines whose halt states obviously cannot be reached based
on backtracking.
"""

from __future__ import division
import copy

from Common import Exit_Condition, HALT_STATE
import IO

# Constants
BACKTRACK = "Backtrack"

def get_info(TTable):
  """Finds all halt transitions, transitions that could get to 
  each state and all of the single-sided symbols."""
  num_states = len(TTable)
  num_symbols = len(TTable[0])
  halts = []
  to_state = [[] for x in range(num_states)]
  dir_to_symbol = [[False, False] for x in range(num_symbols)]
  # The zero symbol is in both directions by default.
  dir_to_symbol[0] = [True, True]
  for state_in in range(num_states):
    for symbol_in in range(num_symbols):
      symbol_out, dir_out, state_out = cell = TTable[state_in][symbol_in]
      if state_out == HALT_STATE:
        # Counts both halting and undefined transitions.
        halts.append((state_in, symbol_in))
      else:
        # Add this input transition to those that can lead to this state.
        to_state[state_out].append(((state_in, symbol_in), cell))
        # And note that that this symbol can be found on the opposite
        # side of the tape (the direction we are moving away from).
        dir_to_symbol[symbol_out][not dir_out] = True
  return halts, to_state, dir_to_symbol

class Partial_Config:
  def __init__(self, state, symbol):
    self.dir = ([], [])
    self.current = symbol
    self.state = state

  def __repr__(self):
    return "%r %r %r %r" % (self.dir[0], self.state, self.current, self.dir[1])

  def applies(self, (state_in, symbol_in), (symbol_out, dir_out, state_out)):
    """Tests whether this transition could have been applied to reach
    this configuration."""
    return len(self.dir[not dir_out]) == 0 or \
           self.dir[not dir_out][0] == symbol_out

  def apply_trans(self, (state_in, symbol_in),
                  (symbol_out, dir_out, state_out)):
    """Return a new configuration with transition applied backwards."""
    new_config = copy.deepcopy(self)
    # Back away from the current symbol.
    new_config.dir[dir_out].insert(0, new_config.current)
    # Step onto the symbol we came from.
    if len(new_config.dir[not dir_out]) != 0:
      del new_config.dir[not dir_out][0]
    # Set the symbol and state to what they must have been to apply this 
    # transition.
    new_config.current = symbol_in
    new_config.state = state_in
    return new_config

def is_init_config(config):
  """Is this config the start configuration? If so, stop backtracking.
  We've proven this machine halts (in the most ass-backwards way :/ )."""
  if config.current != 0 or config.state != 0:
    return False
  for side in config.dir:
    for symbol in side:
      if symbol != 0:
        return False
  return True

def is_possible_config(config, dir_to_symbol):
  """Is this configuration possible? Based solely off of dir_to_symbol
  which stores which symbols can be on which sides of the tape."""
  for dir in range(2):
    for symbol in config.dir[dir]:
      if not dir_to_symbol[symbol][dir]:
        return False
  return True

def backtrack_single_halt((halt_state, halt_symbol),
                          to_state, dir_to_symbol, steps, max_configs):
  """Try backtrackying |steps| steps from this specific halting
  config. |to_state| is a list of transitions that lead to each state.
  |dir_to_symbol| indicates which direction symbols can be found."""
  # All possible configurations leading to halt in i+1 steps.
  pos_configs = [Partial_Config(halt_state, halt_symbol)]
  for i in range(steps):
    # All configurations that could lead to pos_configs in one step.
    prev_configs = []
    for config in pos_configs:
      for addr, cell in to_state[config.state]:
        if config.applies(addr, cell):
          prev_config = config.apply_trans(addr, cell)
          if is_init_config(prev_config):
            # We've proven that we can get to halt from the initial config.
            # Probably this should not happen in practice because we will
            # simulate all machines for more steps forwards before trying
            # to simulate them backwards, but we keep this for correctness.
            return Exit_Condition.HALT, i + 2
          if is_possible_config(prev_config, dir_to_symbol):
            prev_configs.append(prev_config)
    pos_configs = prev_configs
    if len(pos_configs) == 0:
      return Exit_Condition.INFINITE, i + 1
    elif len(pos_configs) > max_configs:
      break
  return Exit_Condition.UNKNOWN, i + 1

def backtrack_ttable(TTable, steps, max_configs):
  """Try backtracking |steps| steps for each halting config in TTable,
  giving up if there are more than |max_configs| possible configs."""
  # Get initial ttable info.
  halts, to_state, dir_to_symbol = get_info(TTable)
  max_steps = -1
  # See if all halts cannot be reached
  for halt_state, halt_symbol in halts:
    # Initial Criterion: no halt_state transition goes to the halt_state
    # For efficiency esp. in multi-symbol situations
    # TODO(shawn): With new improvements, this initial criterion may be
    # stifling.
    # For example, this is why we cannot prove "1RB ---  1LB 1RZ" Halting.
    for symbol_out, dir_out, state_out in TTable[halt_state]:
      if state_out == halt_state:
        return False
    condition, this_steps = backtrack_single_halt((halt_state, halt_symbol),
                                                  to_state, dir_to_symbol,
                                                  steps, max_configs)
    # If any of the backtracks fail, the whole thing fails.
    if condition == Exit_Condition.UNKNOWN:
      return False
    if condition == Exit_Condition.HALT:
      return Exit_Condition.HALT, "?", this_steps
    max_steps = max(max_steps, this_steps)
  # If all halt states cannot be reached:
  return Exit_Condition.INFINITE, BACKTRACK, max_steps, "Backtrack"

def apply_results(results, old_line, log_number):
  old_results = old_line[5]
  return old_line[0:5]+(results, old_line[6], log_number, old_results)

from Option_Parser import Filter_Option_Parser

def main(argv):
  # Get command line options.
  opts, args = Filter_Option_Parser(argv, [
      ("backsteps" , int, None, True, True),
      ("limit",     int, None, False, True)])

  limit = opts["limit"]
  if limit is None:
    limit = opts["backsteps"]
  log_number = opts["log_number"]
  io = IO.IO(opts["infile"], opts["outfile"], log_number)
  next_entry = io.read_result()
  while next_entry:
    TTable = next_entry[6]
    # Run the simulator/filter on this machine
    results = backtrack_ttable(TTable, opts["backsteps"], limit)
    # Deal with result
    if results:
      next_entry = apply_results(results, next_entry, log_number)
    io.write_result_raw(*next_entry)
    next_entry = io.read_result()

if __name__ == "__main__":
  import sys
  main(sys.argv)
