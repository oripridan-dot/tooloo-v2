from dag_orchestrator import DAGOrchestrator

def main():
    orchestrator = DAGOrchestrator()
    orchestrator.run_pipeline()

if __name__ == "__main__":
    main()
