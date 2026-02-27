# src/states/student_states.py

from aiogram.fsm.state import State, StatesGroup

class StudentStudyMode(StatesGroup):
    choosing_mode = State()   
    choosing_theme = State()    
    studying = State()           
    testing = State() 
                 