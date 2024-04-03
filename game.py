import openai  # for calling the OpenAI API
import random
import yaml
from process_case_studies import case_studies

# Pre-train on a given set of case studies
def pretrain(case_studies):
    trained_models = []
    for case_study in case_studies:
        messages = [
        {"role": "system", "content": "You answer questions about the case study without revealing the diagnosis."},
        {"role": "user", "content": case_study['description'] + case_study['details'] + case_study['diagnosis']},
    ]
        response = openai.chat.completions.create(
            model=GPT_MODEL,
            messages=messages,
            max_tokens=100
        )
        trained_models.append((response.model, case_study['description'], case_study['details'], case_study['diagnosis']))
    return trained_models

# Select a pre-trained model for a given round
def select_model(trained_models):
    return random.sample(trained_models, 1)

# Play a round of the game
def play_round(chatbot_model):
    model, description, details, diagnosis = chatbot_model[0]

    print("New round started.")
    print("Here's a brief description of the patient's case:")
    print(description)

    #TODO:
    #type 'guess' to guess diagnosis. should have responses like "close" or "be more specific" maybe
    print("Ask about specific details to diagnose the patient. Type 'guess' to guess the diagnosis. Type 'reveal' to reveal the diagnosis. Type 'quit' to end the round.")
    user_input = input("Your question or command: ")

    while user_input.lower() != 'quit':
        if user_input.lower() == 'reveal':
            print(f"The diagnosis is: {diagnosis}")
        elif user_input.lower() == 'guess':
            if 'guess' == diagnosis:
                print("Correct!")
            else:
                print("Incorrect.")
        else:
            # Respond to the user's question
            #TODO:
            #why do i need to put the case study again?? :(
            messages=[
            {'role': 'system', 'content': 'You answer questions about the case study. When the user asks for the results of a test, answer if the information is in the case study; otherwise say "I do not have that information." Do not reveal diagnosis. Do not make claims that are not stated in the case study or make up statistics. Don’t justify your answers. Don’t give information not mentioned in the case study.'},
            {'role': 'user', 'content': user_input + description + details + diagnosis},
            #{'role': 'user', 'content': "Do not reveal diagnosis. Do not make claims that are not stated in the case study or make up statistics. Don’t justify your answers. Don’t give information not mentioned in the case study."},
            ]
            response = openai.chat.completions.create(
                model=model,
                messages=messages,
                #max_tokens=100
            )
            print(response.choices[0].message.content)#.strip()

        user_input = input("Your question or command: ")


if __name__ == "__main__":

    # gpt model
    EMBEDDING_MODEL = "text-embedding-ada-002"
    GPT_MODEL = "gpt-3.5-turbo"

    with open("config.yaml", 'r') as stream:
        config = yaml.safe_load(stream)

    openai.api_key = config['api_key']
    
    
    # Pre-train the chatbot on the case studies
    trained_models = pretrain(case_studies)

    # multiple rounds
    while True:
        # Select a pre-trained model
        chatbot_model= select_model(trained_models)
        # Get the description for the selected case study
        #description = [case_study['description'] for case_study in case_studies if case_study['diagnosis'] == diagnosis][0]

        # Play the round using the selected chatbot model
        play_round(chatbot_model)

        # Ask if the user wants to play another round
        play_again = input("Do you want to start a new round? (yes/no): ")
        if play_again.lower() != 'yes':
            break