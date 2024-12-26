from pydantic import BaseModel
from typing import Optional, Dict, Any, List, TypedDict

# Add pydantic class dictionary with full paths and descriptions
pydantic_class_dictx = {
    "Engineered Prompt": "self_eval_crew.EngineeredPrompt",
    "Analysis Review State": "self_eval_crew.AnalysisReviewState",
    "Research Results": "self_eval_crew.ResearchResults",
    "None": ""  # Default option
}

  # Enhance pydantic_class_dict with descriptions
enhanced_pydantic_classes = {
      'Engineered Prompt': {
          'path': 'self_eval_crew.EngineeredPrompt',
          'description': 'Structures output as a prompt with rationale for changes. Use for prompt engineering tasks.'
      },
      'Analysis Review State': {
          'path': 'self_eval_crew.AnalysisReviewState',
          'description': 'Tracks analysis state with counter, prompt, rationale, and feedback. Use for review tasks.'
      },
      'Research Results': {
          'path': 'self_eval_crew.ResearchResults',
          'description': 'Organizes research findings in a structured dictionary format. Use for research tasks.'
      },
      'None': {
          'path': '',
          'description': 'No specific output format required. Task will return raw output.'
      }
}


class ResearchResults(BaseModel):
  results: Dict[str, Any]

class EngineeredPrompt(BaseModel):
    prompt: str = ""
    prompt_change_rationale: str = ""

class AnalysisReviewState(BaseModel):
    counter: int = 0
    prompt: str = ""
    prompt_change_rationale: str = ""
    research: str = ""
    success_flag: bool = False
    feedback: str = ""