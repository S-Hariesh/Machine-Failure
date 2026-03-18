from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView, PasswordResetView, PasswordChangeView
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.views import View
from django.contrib.auth.decorators import login_required 
from django.contrib.auth import logout as auth_logout
import numpy as np
import joblib
from .forms import RegisterForm, LoginForm, UpdateUserForm, UpdateProfileForm
from . models import UserPredictModel
from .forms import UserPredictDataForm



# import serial

# ser = serial.Serial()
# ser.port = 'COM6
# ser.baudrate = 9600
# ser.bytesize = 8
# ser.parity = serial.PARITY_NONE
# ser.stopbits = serial.STOPBITS_ONE

# import time
# import re

# def serialget():
#     value=[]
#     ser.open()
#     time.sleep(1)
#     v=b'A'
#     ser.write(v)
#     while True:
#         for line in ser.read():
#             if chr(line) != '#':
#                 value.append(chr(line))
#             else:
#                 print("end")
#                 ser.close()
#                 return value


# def request(request):
#     str1=''
#     val=[]
#     va=serialget()
#     print(va)
#     for v in va:
#         if(v=='*'):
#             continue
#         else:  
#             if(v!='$'): 
#                 str1+=v
#             else:
#                 print(str1)
#                 cleaned_str = re.sub(r'[^0-9.,]', '', str1)
#                 try:
#                     val = [float(num) for num in cleaned_str.split(',')]
#                 except ValueError:
#                     print(f"Error converting {cleaned_str} to float.")
#                 str1=""





import firebase_admin
from firebase_admin import credentials, db
from django.http import JsonResponse



cred = credentials.Certificate("C:/Users/harie/Downloads/Machine Failure (1)/Machine Failure/Deployment/users/machine-772d9-firebase-adminsdk-fbsvc-197452558d.json")


if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://machine-772d9-default-rtdb.firebaseio.com/'
    })


from django.http import JsonResponse


import random

MOCK_DATASET = [
    # [Air Temp (K), Process Temp (K), RPM, Torque (Nm), Tool Wear (min)]
    # We only inject TEMP(0), RPM(2), VIB/Torque(3) into the live feed simulator
    [298.1, 308.6, 1551.0, 42.8, 0.0],   # Normal
    [302.3, 311.5, 1400.0, 60.5, 210.0], # Tool Wear / Overstrain
    [299.0, 310.0, 2800.0, 15.0, 10.0],  # Power Failure
    [304.5, 313.2, 1350.0, 65.0, 50.0],  # Heat Dissipation / Overstrain
    [298.5, 309.1, 1450.0, 45.3, 5.0],   # Normal
    [300.2, 310.5, 1200.0, 70.0, 80.0],  # High Torque (Tool Wear or Overstrain)
]

def fetch_firebase_data(request):
    mode = request.GET.get('mode', 'live')

    if mode == 'test':
        row = random.choice(MOCK_DATASET)
        data2 = row[0]  # Air Temp
        data  = row[2]  # RPM
        data3 = row[3]  # Torque / VIB
        connected = True
        is_test_mode = True
    else:
        ref1 = db.reference('/Monitoring/RPM')
        ref2 = db.reference('/Monitoring/TEMP')
        ref3 = db.reference('/Monitoring/VIB')
        data = ref1.get()
        data2 = ref2.get()
        data3 = ref3.get()
        connected = (data is not None or data2 is not None or data3 is not None)
        is_test_mode = False

    pred_label = None
    ret_process_temp = None
    ret_tool_wear = None

    if connected:
        try:
            air_temp = float(data2) if data2 is not None else 300.0
            process_temp = air_temp + 10.0
            rot_speed = float(data) if data is not None else 1500.0
            torque = float(data3) if data3 is not None else 40.0
            
            # Use appropriate tool wear depending on mode
            if is_test_mode:
                tool_wear = row[4] # Use exact tool wear from mock subset
                process_temp = row[1]
            else:
                tool_wear = 0.0

            ret_process_temp = process_temp
            ret_tool_wear = tool_wear

            features = [np.array([air_temp, process_temp, rot_speed, torque, tool_wear])]
            prediction = Model.predict(features)[0]

            labels = {
                0: 'Heat Dissipation Failure',
                1: 'No Failure',
                2: 'Overstrain Failure',
                3: 'Power Failure',
                4: 'Random Failures',
                5: 'Tool Wear Failure'
            }
            pred_label = labels.get(prediction, 'Unknown Validation')
        except Exception as e:
            print(f"Prediction Error: {e}")
            pred_label = 'Calculation Error'

    return JsonResponse({
        'rpm': data,
        'temp': data2,
        'vib': data3,
        'process_temp': ret_process_temp,
        'tool_wear': ret_tool_wear,
        'connected': connected,
        'prediction': pred_label,
        'mode': mode
    })
        








import firebase_admin
from firebase_admin import credentials,db

def initialize_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate("users/machine-772d9-firebase-adminsdk-fbsvc-197452558d.json")
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://machine-772d9-default-rtdb.firebaseio.com/'  # Replace with your database URL
        })

initialize_firebase()
ref = db.reference('Monitoring')



        

def home(request):
    return render(request, 'users/home.html')

@login_required(login_url='users-register')


def index(request):
    return render(request, 'app/index.html')

class RegisterView(View):
    form_class = RegisterForm
    initial = {'key': 'value'}
    template_name = 'users/register.html'

    def dispatch(self, request, *args, **kwargs):
        # will redirect to the home page if a user tries to access the register page while logged in
        if request.user.is_authenticated:
            return redirect(to='/')

        # else process dispatch as it otherwise normally would
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = self.form_class(initial=self.initial)
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)

        if form.is_valid():
            form.save()

            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}')

            return redirect(to='login')

        return render(request, self.template_name, {'form': form})


# Class based view that extends from the built in login view to add a remember me functionality

class CustomLoginView(LoginView):
    form_class = LoginForm

    def form_valid(self, form):
        remember_me = form.cleaned_data.get('remember_me')

        if not remember_me:
            # set session expiry to 0 seconds. So it will automatically close the session after the browser is closed.
            self.request.session.set_expiry(0)

            # Set session as modified to force data updates/cookie to be saved.
            self.request.session.modified = True

        # else browser session will be as long as the session cookie time "SESSION_COOKIE_AGE" defined in settings.py
        return super().form_valid(form)


class ResetPasswordView(SuccessMessageMixin, PasswordResetView):
    template_name = 'users/password_reset.html'
    email_template_name = 'users/password_reset_email.html'
    subject_template_name = 'users/password_reset_subject'
    success_message = "We've emailed you instructions for setting your password, " \
                      "if an account exists with the email you entered. You should receive them shortly." \
                      " If you don't receive an email, " \
                      "please make sure you've entered the address you registered with, and check your spam folder."
    success_url = reverse_lazy('users-home')


class ChangePasswordView(SuccessMessageMixin, PasswordChangeView):
    template_name = 'users/change_password.html'
    success_message = "Successfully Changed Your Password"
    success_url = reverse_lazy('users-home')


@login_required
def profile(request):
    if request.method == 'POST':
        user_form = UpdateUserForm(request.POST, instance=request.user)
        profile_form = UpdateProfileForm(request.POST, request.FILES, instance=request.user.profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile is updated successfully')
            return redirect(to='users-profile')
    else:
        user_form = UpdateUserForm(instance=request.user)
        profile_form = UpdateProfileForm(instance=request.user.profile)

    return render(request, 'users/profile.html', {'user_form': user_form, 'profile_form': profile_form})



Model = joblib.load('users/Best_Model.pkl')
def model(request):
    if request.method == 'POST':
        fields =['Air_temperature', 'Process_temperature', 'Rotational_speed', 'Torque', 'Tool_wear']
      
        
        form = UserPredictDataForm(request.POST)
        features = []
        for i in fields:
            info = float(request.POST[i])
            features.append(info)
           
        Final_features = [np.array(features, dtype=int)]
        
        prediction = Model.predict(Final_features)
        actual_output = prediction[0]
        print(actual_output)

        if actual_output == 0:
            initialize_firebase()
            ref = db.reference('Monitoring')
            # Store info directly as a value
            ref.update({
                'PYDATA': 'A'
            })
            actual_output1 = 'Heat Dissipation Failure'
            
        elif actual_output == 1:
            initialize_firebase()
            ref = db.reference('Monitoring')
            # Store info directly as a value
            ref.update({
                'PYDATA': 'B'
            })
            actual_output1 = 'No Failure'
        
        elif actual_output == 2:
            initialize_firebase()
            ref = db.reference('Monitoring')
            # Store info directly as a value
            ref.update({
                'PYDATA': 'C'
            })
            actual_output1 = 'Overstrain Failure'

        elif actual_output == 3:
            initialize_firebase()
            ref = db.reference('Monitoring')
            # Store info directly as a value
            ref.update({
                'PYDATA': 'D'
            })
            actual_output1 = 'Power Failure'

        elif actual_output == 4:
            initialize_firebase()
            ref = db.reference('Monitoring')
            # Store info directly as a value
            ref.update({
                'PYDATA': 'E'
            })
            actual_output1 = 'Random Failures'

        elif actual_output == 5:
            initialize_firebase()
            ref = db.reference('Monitoring')
            # Store info directly as a value
            ref.update({
                'PYDATA': 'F'
            })
            actual_output1 = 'Tool Wear Failure'


      
        print("output",actual_output1)
        if form.is_valid():
            print('Saving data in Form')
            form_instance = form.save()  # Save form data but don't commit to DB yet
            form_instance.save()
        data = UserPredictModel.objects.latest('id')
        data.Label = actual_output1
        data.save()
        return render(request, 'app/result.html', {'form':form, 'prediction_text':actual_output1})
    else:
        print('Else working')
        form = UserPredictDataForm(request.POST)    
    return render(request, 'app/model.html', {'form':form})


from .models import Profile
def profile_database(request):

    data=Profile.objects.all()
    
    return render(request,'app/profile_list.html',{'database':data})




 
