
from commands.eval.classes.run_settings import RunSettings
from pathlib import Path

def main():
	s2 = RunSettings()
	print(s2.use_score_threshold)
	print (s2.score_threshold)     
	  
if __name__ == "__main__":
	main()
