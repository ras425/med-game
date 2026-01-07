#!/usr/bin/env python3

from google import genai
import random
import yaml
from process_case_studies import load_cases

# colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'


GEMINI_MODEL = "gemini-2.5-flash"


class MedicalDiagnosisGame:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.case_studies = load_cases()
        self.used_cases = []
        self.score = 0
        self.rounds_played = 0
        self.hints_used = 0
        
    def reset_cases(self):
        self.used_cases = []
        print(f"\n{Colors.CYAN} Completed all cases ! reshuffling...{Colors.RESET}\n")
    
    def select_case(self) -> dict:
        available_cases = [c for c in self.case_studies if c not in self.used_cases]
        
        if not available_cases:
            self.reset_cases()
            available_cases = self.case_studies.copy()
        
        case = random.choice(available_cases)
        self.used_cases.append(case)
        return case
    
    def check_guess(self, guess: str, case: dict) -> tuple[bool, str]:
        prompt = f"""You are a medical professor evaluating a student's diagnosis.

The correct diagnosis is: {case['diagnosis']}
The student guessed: {guess}

Evaluate if the student's guess is correct. Consider:
- Exact matches are correct
- Equivalent medical terms are correct (e.g., "heart attack" = "myocardial infarction")
- Common abbreviations are correct (e.g., "PE" = "pulmonary embolism")
- Partial matches that are too vague are CLOSE (e.g., guessing "infection" when answer is "pneumonia")

Respond in this exact format:
VERDICT: [CORRECT/CLOSE/INCORRECT]
HINT: [If incorrect or close, give a brief educational hint to steer them toward the right answer without revealing it. Compare their guess to the correct diagnosis and suggest what they should consider or ask about.]"""
        
        try:
            response = self.client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt
            )
            result = response.text.strip()
            
            if "VERDICT: CORRECT" in result.upper():
                return True, "Correct!"
            else:
                hint = "Think about what else could explain these symptoms."
                if "HINT:" in result:
                    hint = result.split("HINT:")[-1].strip()
                if "VERDICT: CLOSE" in result.upper():
                    return False, f"{Colors.YELLOW}Close! {hint}{Colors.RESET}"
                else:
                    return False, f"{Colors.YELLOW}Not quite. {hint}{Colors.RESET}"
        except Exception as e:
            if guess.lower().strip() == case['diagnosis'].lower().strip():
                return True, "Correct!"
            return False, f"{Colors.YELLOW}Not quite. Consider what other conditions could cause these symptoms.{Colors.RESET}"
    
    def ask_question(self, question: str, case: dict, conversation_history: list) -> str:
        conversation_history.append(f"User: {question}")
        
        history_text = "\n".join(conversation_history[-10:])  # keep last 10 exchanges
        
        prompt = f"""You are a medical case presenter. Answer questions about this patient case.

CASE DESCRIPTION: {case['description']}

CASE DETAILS: {case['details']}

DIAGNOSIS (DO NOT REVEAL): {case['diagnosis']}

CONVERSATION SO FAR:
{history_text}

Rules:
1. NEVER reveal the diagnosis directly
2. Only provide information that is explicitly stated in the case
3. If asked about a test not mentioned, say "That test was not performed" or "That information is not available"
4. Be concise and clinical in your responses
5. Do not make up statistics or findings not in the case
6. If the user asks leading questions about the diagnosis, deflect without confirming or denying

Respond to the user's latest question:"""

        try:
            response = self.client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt
            )
            answer = response.text.strip()
            conversation_history.append(f"Assistant: {answer}")
            return answer
        except Exception as e:
            return f"Error getting response: {str(e)}"
    
    def get_hint(self, case: dict, hints_given: int) -> str:
        """Provide a hint by revealing a fact from the case details."""
        details = case.get('details', '')
        
        # Split details into individual facts/sentences
        facts = [s.strip() for s in details.replace('\n', '. ').split('. ') if s.strip() and len(s.strip()) > 10]
        
        if not facts:
            return "Review the patient's presentation carefully."
        
        # Return facts one at a time
        if hints_given < len(facts):
            return f"Additional finding: {facts[hints_given]}"
        else:
            # All facts revealed, give a thinking prompt
            return "You've seen all the available findings. What diagnosis fits this clinical picture?"
    
    def display_welcome(self):
        print(f"""
{Colors.CYAN}{'═' * 60}{Colors.RESET}
{Colors.BOLD}{Colors.HEADER}
    ╔╦╗╔═╗╔╦╗╦╔═╗╔═╗╦    ╔╦╗╦╔═╗╔═╗╔╗╔╔═╗╔═╗╦╔═╗
    ║║║║╣  ║║║║  ╠═╣║     ║║║╠═╣║ ╦║║║║ ║╚═╗║╚═╗
    ╩ ╩╚═╝═╩╝╩╚═╝╩ ╩╩═╝  ═╩╝╩╩ ╩╚═╝╝╚╝╚═╝╚═╝╩╚═╝
                    🏥 GAME 🏥
{Colors.RESET}
{Colors.CYAN}{'═' * 60}{Colors.RESET}

{Colors.YELLOW}Welcome, Doctor! Test your diagnostic skills.{Colors.RESET}

You will be presented with patient cases. Ask questions to 
gather information and guess the diagnosis!

{Colors.BOLD}Commands:{Colors.RESET}
  • Type questions to investigate the case
  • {Colors.GREEN}'guess'{Colors.RESET}  - Submit your diagnosis
  • {Colors.YELLOW}'hint'{Colors.RESET}   - Get a hint
  • {Colors.BLUE}'reveal'{Colors.RESET} - Give up and see the answer
  • {Colors.RED}'quit'{Colors.RESET}   - End the current round

{Colors.BOLD}Scoring:{Colors.RESET}
  • Correct guess: +100 points
  • Each hint used: -15 points
  • Revealing answer: -50 points

{Colors.DIM}Powered by Google Gemini (Free){Colors.RESET}
{Colors.CYAN}{'═' * 60}{Colors.RESET}
""")

    def display_case(self, case: dict):
        """Display the case description."""
        print(f"""
{Colors.CYAN}{'─' * 60}{Colors.RESET}
{Colors.BOLD}{Colors.HEADER}📋 NEW PATIENT CASE{Colors.RESET}
{Colors.CYAN}{'─' * 60}{Colors.RESET}

{Colors.YELLOW}Chief Complaint:{Colors.RESET}
{case['description']}
{Colors.DIM}Ask questions to learn more about the patient...{Colors.RESET}
{Colors.CYAN}{'─' * 60}{Colors.RESET}
""")

    def play_round(self) -> bool:
        """
        Play a single round of the game.
        Returns True if player wants to continue, False otherwise.
        """
        case = self.select_case()
        self.rounds_played += 1
        round_hints = 0
        round_score = 100
        conversation_history = []
        
        self.display_case(case)
        
        while True:
            print(f"\n{Colors.DIM}[Score: {self.score} | Round: {self.rounds_played} | Available: guess, hint, reveal, quit]{Colors.RESET}")
            user_input = input(f"{Colors.BOLD}Your question: {Colors.RESET}").strip()
            
            if not user_input:
                continue
            
            command = user_input.lower()
            
            if command == 'quit':
                print(f"\n{Colors.YELLOW}Ending round...{Colors.RESET}")
                return False
            
            elif command == 'reveal':
                round_score = max(0, round_score - 50)
                print(f"\n{Colors.RED}{'─' * 40}{Colors.RESET}")
                print(f"{Colors.BOLD}The diagnosis was: {Colors.CYAN}{case['diagnosis']}{Colors.RESET}")
                print(f"{Colors.RED}{'─' * 40}{Colors.RESET}")
                print(f"{Colors.DIM}Points for this round: 0{Colors.RESET}")
                break
            
            elif command == 'hint':
                round_hints += 1
                round_score = max(0, round_score - 15)
                hint = self.get_hint(case, round_hints - 1)
                print(f"\n{Colors.YELLOW}💡 Hint #{round_hints}: {hint}{Colors.RESET}")
                print(f"{Colors.DIM}(-15 points){Colors.RESET}")
            
            elif command == 'guess':
                guess = input(f"{Colors.BOLD}Enter your diagnosis: {Colors.RESET}").strip()
                if guess:
                    is_correct, feedback = self.check_guess(guess, case)
                    
                    if is_correct:
                        print(f"\n{Colors.GREEN}{'═' * 40}{Colors.RESET}")
                        print(f"{Colors.BOLD}{Colors.GREEN}🎉 {feedback}{Colors.RESET}")
                        print(f"{Colors.GREEN}The diagnosis is: {case['diagnosis']}{Colors.RESET}")
                        print(f"{Colors.GREEN}{'═' * 40}{Colors.RESET}")
                        final_score = max(0, round_score)
                        self.score += final_score
                        self.hints_used += round_hints
                        print(f"\n{Colors.CYAN}Points earned: +{final_score}{Colors.RESET}")
                        print(f"{Colors.BOLD}Total score: {self.score}{Colors.RESET}")
                        break
                    else:
                        print(f"\n{feedback}")
            
            else:
                # Ask a question about the case
                print(f"\n{Colors.BLUE}🩺 {Colors.RESET}", end="")
                response = self.ask_question(user_input, case, conversation_history)
                print(response)
        
        # Ask to play again
        print()
        play_again = input(f"{Colors.BOLD}Play another round? (yes/no): {Colors.RESET}").strip().lower()
        return play_again in ['yes', 'y']
    
    def display_final_score(self):
        print(f"""
{Colors.CYAN}{'═' * 60}{Colors.RESET}
{Colors.BOLD}{Colors.HEADER}🏆 GAME OVER 🏆{Colors.RESET}
{Colors.CYAN}{'═' * 60}{Colors.RESET}

{Colors.BOLD}Final Statistics:{Colors.RESET}
  • Rounds played: {self.rounds_played}
  • Total score: {Colors.GREEN}{self.score}{Colors.RESET}
  • Hints used: {self.hints_used}
  • Average score per round: {self.score / max(1, self.rounds_played):.1f}

{Colors.YELLOW}Thanks for playing, Doctor! {Colors.RESET}

{Colors.CYAN}{'═' * 60}{Colors.RESET}
""")
    
    def run(self):
        """Main game loop."""
        self.display_welcome()
        
        input(f"{Colors.BOLD}Press Enter to start...{Colors.RESET}")
        
        playing = True
        while playing:
            playing = self.play_round()
        
        self.display_final_score()


def main():
    """Entry point for the game."""
    # Load configuration
    try:
        with open("config.yml", 'r') as stream:
            config = yaml.safe_load(stream)
    except FileNotFoundError:
        print(f"{Colors.RED}Error: config.yml not found!{Colors.RESET}")
        print("Please create a config.yml file with your Google Gemini API key:")
        print('  api_key: "your-gemini-api-key-here"')
        print(f"\n{Colors.YELLOW}Get a free API key at: https://aistudio.google.com/apikey{Colors.RESET}")
        return
    
    api_key = config.get('api_key')
    if not api_key or api_key == "YOUR_API_KEY_HERE":
        print(f"{Colors.RED}Error: Please set your Google Gemini API key in config.yml{Colors.RESET}")
        print(f"\n{Colors.YELLOW}Get a free API key at: https://aistudio.google.com/apikey{Colors.RESET}")
        return
    
    game = MedicalDiagnosisGame(api_key)
    game.run()


if __name__ == "__main__":
    main()
