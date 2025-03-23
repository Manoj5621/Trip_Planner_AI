import os
import json
import openai
import google.generativeai as genai
from anthropic import Anthropic
from django.core.exceptions import ValidationError

class AITripPlanner:
    def __init__(self, provider='google'):
        self.provider = provider
        if provider == 'openai':
            openai.api_key = os.getenv('OPENAI_API_KEY')
        elif provider == 'google':
            api_key = os.getenv('GOOGLE_API_KEY')
            if not api_key:
                raise ValidationError("Google API key not found in environment variables")
            try:
                genai.configure(api_key=api_key)
                # Configure the model with safety settings
                generation_config = {
                    "temperature": 0.9,
                    "top_p": 1,
                    "top_k": 1,
                    "max_output_tokens": 2048,
                }
                safety_settings = [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                ]

                # Initialize the model with gemini-1.5-flash
                self.model = genai.GenerativeModel(
                    model_name="gemini-1.5-flash",
                    generation_config=generation_config,
                    safety_settings=safety_settings
                )
                
                # Test the configuration with a simple prompt
                response = self.model.generate_content("Hello")
                if not response:
                    raise ValidationError("Could not initialize Google AI model")
            except Exception as e:
                raise ValidationError(f"Error configuring Google AI: {str(e)}")
        elif provider == 'anthropic':
            self.anthropic = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

    def _generate_prompt(self, trip_data):
        days = (trip_data['end_date'] - trip_data['start_date']).days + 1
        json_template = '''
{
    "day_1": {
        "morning": {
            "main": "Primary morning activity",
            "alternatives": ["Alternative 1", "Alternative 2"]
        },
        "afternoon": {
            "main": "Primary afternoon activity",
            "alternatives": ["Alternative 1", "Alternative 2"]
        },
        "evening": {
            "main": "Primary evening activity",
            "alternatives": ["Alternative 1", "Alternative 2"]
        },
        "food": ["Restaurant 1", "Restaurant 2"],
        "tips": "Daily tips and notes"
    }
}'''

        prompt = f"""Create a detailed {days}-day trip itinerary for a {trip_data['trip_type'].lower()} trip to {trip_data['destination']} 
from {trip_data['start_location']} for {trip_data['number_of_people']} people.
Start Date: {trip_data['start_date']}
End Date: {trip_data['end_date']}
Interested Activities: {trip_data['interested_activities']}

For each day, provide:
1. Morning activities with 2 alternative options
2. Afternoon activities with 2 alternative options
3. Evening activities with 2 alternative options
4. Recommended restaurants or food experiences
5. Travel tips and notes

Format the response as a JSON object with the following structure:
{json_template}"""
        return prompt

    def _parse_ai_response(self, response_text):
        """Parse the AI response and ensure it's in the correct format"""
        try:
            # Try to parse the response as JSON
            if isinstance(response_text, dict):
                return response_text
            
            # If it's a string, try to extract JSON from it
            # Sometimes AI might include explanatory text before/after the JSON
            response_text = response_text.strip()
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                return json.loads(json_str)
            
            raise ValueError("Could not find valid JSON in response")
            
        except Exception as e:
            # If parsing fails, return an error message in the expected format
            return {
                "day_1": {
                    "morning": {
                        "main": "Error generating itinerary",
                        "alternatives": ["Please try again", "Contact support if the issue persists"]
                    },
                    "afternoon": {
                        "main": "Error generating itinerary",
                        "alternatives": ["Please try again", "Contact support if the issue persists"]
                    },
                    "evening": {
                        "main": "Error generating itinerary",
                        "alternatives": ["Please try again", "Contact support if the issue persists"]
                    },
                    "food": ["Error generating restaurant recommendations"],
                    "tips": f"Error: {str(e)}"
                }
            }

    def generate_trip_plan(self, trip_data):
        prompt = self._generate_prompt(trip_data)
        
        try:
            if self.provider == 'openai':
                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}]
                )
                return self._parse_ai_response(response.choices[0].message.content)

            elif self.provider == 'google':
                response = self.model.generate_content(prompt)
                if response.text:
                    return self._parse_ai_response(response.text)
                else:
                    raise ValidationError("No response generated from Google AI")

            elif self.provider == 'anthropic':
                response = self.anthropic.messages.create(
                    model="claude-3-opus-20240229",
                    max_tokens=4000,
                    messages=[{"role": "user", "content": prompt}]
                )
                return self._parse_ai_response(response.content[0].text)
                
        except Exception as e:
            return {
                "error": str(e),
                "day_1": {
                    "morning": {
                        "main": "Error occurred while generating trip plan",
                        "alternatives": ["Please try again later", "Contact support if the issue persists"]
                    },
                    "afternoon": {
                        "main": "Error occurred while generating trip plan",
                        "alternatives": ["Please try again later", "Contact support if the issue persists"]
                    },
                    "evening": {
                        "main": "Error occurred while generating trip plan",
                        "alternatives": ["Please try again later", "Contact support if the issue persists"]
                    },
                    "food": ["Error generating recommendations"],
                    "tips": f"Error: {str(e)}"
                }
            } 