import pyttsx3
import speech_recognition as sr

r = sr.Recognizer()

def record_text(): # speech to text
    try:
        with sr.Microphone() as source:
            print("Listening...")
            r.adjust_for_ambient_noise(source, duration=0.2)

            audio = r.listen(source)

            text = r.recognize_google(audio)
            return text

    except sr.RequestError as e:
        print("API error:", e)

    except sr.UnknownValueError:
        print("Could not understand audio")
    return None


def speak(text):
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()


def ask(prompt):
    speak(prompt)
    text = record_text()
    
    if text:
        text = text.upper()
        print("You said:", text)
        return text
    else:
        speak("Sorry, I didn't catch that.")
        return ask(prompt)




