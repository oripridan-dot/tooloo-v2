from abc import ABC, abstractmethod

class BaseNode(ABC):
    def __init__(self, node_id):
        self.node_id = node_id

    @abstractmethod
    def execute(self, *args, **kwargs):
        pass

class DataIngestionNode(BaseNode):
    def execute(self, *args, **kwargs):
        print(f"Executing DataIngestionNode: {self.node_id}")
        # Placeholder for data ingestion logic
        return "ingested_data"

class ProcessingNode(BaseNode):
    def execute(self, data, *args, **kwargs):
        print(f"Executing ProcessingNode: {self.node_id} with data: {data}")
        # Placeholder for data processing logic
        return "processed_data"

class AnalysisNode(BaseNode):
    def execute(self, processed_data, *args, **kwargs):
        print(f"Executing AnalysisNode: {self.node_id} with processed_data: {processed_data}")
        # Placeholder for analysis logic
        return "analysis_results"

class OutputNode(BaseNode):
    def execute(self, analysis_results, *args, **kwargs):
        print(f"Executing OutputNode: {self.node_id} with analysis_results: {analysis_results}")
        # Placeholder for output generation
        return "final_output"
