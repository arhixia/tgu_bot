# src/states/student_states.py

from aiogram.fsm.state import State, StatesGroup

class StudentStudyMode(StatesGroup):
    choosing_mode = State()   
    choosing_theme = State()    
    studying = State()       
    studying_waiting_retry = State()     
    studying_waiting_photo = State()
    testing = State() 
    
                 