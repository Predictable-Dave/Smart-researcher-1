import json
import os
import pandas as pd

def load_json_data(json_string):
  """
  Loads JSON data from a string.

  Args:
      json_string (str): The JSON string to be parsed.

  Returns:
      dict: The parsed JSON data as a Python dictionary.
      None: If the JSON string is invalid.
  """
  
  return json.loads(json_string)


def create_pivot_table_df(data):
  """
  Converts a nested dictionary into a pandas DataFrame suitable for Excel pivot tables.

  Args:
      data: The nested dictionary to convert.

  Returns:
      pandas.DataFrame: The converted DataFrame.
  """

  def _unpack_dict(data, parent_keys=[]):
      """
      Recursively unpacks a dictionary into a list of rows.

      Args:
          data: The dictionary to unpack.
          parent_keys: A list of parent keys for the current level.

      Returns:
          list: A list of dictionaries, where each dictionary represents a row.
      """
      rows = []
      for key, value in data.items():
          if isinstance(value, list):
              for item in value:
                  if isinstance(item, dict):
                      rows.extend(_unpack_dict(item, parent_keys + [key]))
                  else:
                      rows.append({**dict(zip(parent_keys, [item] * len(parent_keys))), key: item})
          elif isinstance(value, dict):
              rows.extend(_unpack_dict(value, parent_keys + [key]))
          else:
              rows.append({**dict(zip(parent_keys, [value] * len(parent_keys))), key: value})
      return rows

  rows = _unpack_dict(data)
  return pd.DataFrame(rows)