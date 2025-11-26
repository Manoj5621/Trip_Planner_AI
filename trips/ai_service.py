import os
import json
from datetime import date
from typing import Any, Dict

import openai
import google.generativeai as genai
from anthropic import Anthropic
from django.core.exceptions import ValidationError


class AITripPlanner:
    def __init__(self, provider: str = 'google'):
        self.provider = provider

        if provider == 'openai':
            key = os.getenv('OPENAI_API_KEY')
            if not key:
                raise ValidationError('OpenAI API key not found in environment variables')
            openai.api_key = key

        elif provider == 'google':
            api_key = os.getenv('GOOGLE_API_KEY')
            if not api_key:
                raise ValidationError('Google API key not found in environment variables')

            try:
                genai.configure(api_key=api_key)

                # Some SDK versions expose a helper method, others require using top-level generate methods.
                # We do a lightweight smoke-test call using a short prompt and keep a small timeout.
                try:
                    # prefer generate_text if available
                    resp = genai.generate_text(model='models/gemini-2.5-flash', prompt='Hello', max_output_tokens=16)
                    text = self._extract_text_from_genai_response(resp)
                except Exception:
                    # fallback: try the newer GenerativeModel if present
                    Model = getattr(genai, 'GenerativeModel', None)
                    if Model:
                        model = Model(model_name='models/gemini-2.5-flash')
                        resp = model.generate_content('Hello')
                        text = self._extract_text_from_genai_response(resp)
                    else:
                        raise

                if not text:
                    raise ValidationError('Could not initialize Google AI model: empty response')

                # keep reference for some SDKs (model object), but not required for top-level generate_text
                self.genai_model = None
                if 'resp' in locals():
                    self.genai_model = resp

            except Exception as e:
                raise ValidationError(f'Error configuring Google AI: {e}')

        elif provider == 'anthropic':
            key = os.getenv('ANTHROPIC_API_KEY')
            if not key:
                raise ValidationError('Anthropic API key not found in environment variables')
            self.anthropic = Anthropic(api_key=key)

    def _generate_prompt(self, trip_data: Dict[str, Any]) -> str:
        # support both date and datetime.date types
        if isinstance(trip_data.get('start_date'), date) and isinstance(trip_data.get('end_date'), date):
            days = (trip_data['end_date'] - trip_data['start_date']).days + 1
        else:
            days = trip_data.get('number_of_days', 1)

        json_template = '''{
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

        prompt = (
            f"Create a detailed {days}-day trip itinerary for a {trip_data.get('trip_type','').lower()} "
            f"trip to {trip_data.get('destination','')} from {trip_data.get('start_location','')} for "
            f"{trip_data.get('number_of_people','1')} people.\n"
            f"Start Date: {trip_data.get('start_date')}\n"
            f"End Date: {trip_data.get('end_date')}\n"
            f"Interested Activities: {trip_data.get('interested_activities','')}\n\n"
            "For each day, provide:\n"
            "1. Morning activities with 2 alternative options\n"
            "2. Afternoon activities with 2 alternative options\n"
            "3. Evening activities with 2 alternative options\n"
            "4. Recommended restaurants or food experiences\n"
            "5. Travel tips and notes\n\n"
            "Format the response as a JSON object with the following structure:\n"
            f"{json_template}"
        )
        return prompt

    def _extract_text_from_genai_response(self, response: Any) -> str:
        try:
            # if SDK returns a plain string
            if isinstance(response, str) and response:
                return response.strip()

            # response may be a dict-like from genai.generate_text
            if isinstance(response, dict):
                # candidate content path
                candidates = response.get('candidates') or []
                for c in candidates:
                    content = c.get('content') or c.get('display') or c.get('text')
                    if isinstance(content, str) and content:
                        return content.strip()

            # objects from newer SDKs
            if hasattr(response, 'text') and response.text:
                return response.text.strip()

            if hasattr(response, 'candidates'):
                for cand in getattr(response, 'candidates') or []:
                    # candidate may have content.parts[].text
                    content = getattr(cand, 'content', None) or getattr(cand, 'display', None)
                    if isinstance(content, str) and content:
                        return content.strip()
                    parts = getattr(content, 'parts', None) or []
                    for p in parts:
                        t = getattr(p, 'text', None)
                        if t:
                            return t.strip()
        except Exception:
            pass

        return ''

    def _parse_ai_response(self, response_text: Any) -> Dict[str, Any]:
        try:
            if isinstance(response_text, dict):
                return response_text

            response_text = (response_text or '').strip()
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1

            if start_idx >= 0 and end_idx > start_idx:
                return json.loads(response_text[start_idx:end_idx])

            # try loading the whole string
            return json.loads(response_text)

        except Exception as e:
            return {
                "day_1": {
                    "morning": {"main": "Error generating itinerary", "alternatives": ["Please try again", "Contact support if the issue persists"]},
                    "afternoon": {"main": "Error generating itinerary", "alternatives": ["Please try again", "Contact support if the issue persists"]},
                    "evening": {"main": "Error generating itinerary", "alternatives": ["Please try again", "Contact support if the issue persists"]},
                    "food": ["Error generating restaurant recommendations"],
                    "tips": f"Error: {e}"
                }
            }

    def generate_trip_plan(self, trip_data: Dict[str, Any]) -> Dict[str, Any]:
        prompt = self._generate_prompt(trip_data)

        try:
            if self.provider == 'openai':
                resp = openai.ChatCompletion.create(model='gpt-4', messages=[{'role': 'user', 'content': prompt}])
                # robust extraction
                content = None
                if isinstance(resp, dict):
                    choices = resp.get('choices') or []
                    if choices:
                        msg = choices[0].get('message') or {}
                        content = msg.get('content') or choices[0].get('text')
                else:
                    content = getattr(resp, 'choices', [None])[0]

                return self._parse_ai_response(content)

            elif self.provider == 'google':
                # try top-level generate_text first
                text = ''
                try:
                    resp = genai.generate_text(model='models/gemini-2.5-flash', prompt=prompt, max_output_tokens=2048, temperature=0.9)
                    text = self._extract_text_from_genai_response(resp)
                except Exception:
                    # fallback: GenerativeModel usage
                    Model = getattr(genai, 'GenerativeModel', None)
                    if Model:
                        model = Model(model_name='models/gemini-2.5-flash')
                        resp = model.generate_content(prompt)
                        text = self._extract_text_from_genai_response(resp)

                if text:
                    return self._parse_ai_response(text)

                # debugging info preserved
                info = []
                resp_obj = locals().get('resp')
                if resp_obj is not None:
                    # try to collect finish reasons
                    cands = getattr(resp_obj, 'candidates', None) or (resp_obj.get('candidates') if isinstance(resp_obj, dict) else [])
                    for cand in cands or []:
                        fr = getattr(cand, 'finish_reason', None) or (cand.get('finish_reason') if isinstance(cand, dict) else None)
                        info.append(f"candidate_finish_reason={fr}")

                raise ValidationError(f"No response generated from Google AI. {'; '.join(info)}")

            elif self.provider == 'anthropic':
                # use the completions endpoint
                resp = self.anthropic.completions.create(model='claude-3-opus-20240229', prompt=prompt, max_tokens_to_sample=4000)
                text = ''
                if isinstance(resp, dict):
                    text = resp.get('completion') or resp.get('text') or ''
                else:
                    text = getattr(resp, 'completion', '') or getattr(resp, 'text', '')

                return self._parse_ai_response(text)

            else:
                raise ValidationError(f'Unknown provider: {self.provider}')

        except Exception as e:
            return {
                'error': str(e),
                'day_1': {
                    'morning': {'main': 'Error occurred while generating trip plan', 'alternatives': ['Please try again later', 'Contact support if the issue persists']},
                    'afternoon': {'main': 'Error occurred while generating trip plan', 'alternatives': ['Please try again later', 'Contact support if the issue persists']},
                    'evening': {'main': 'Error occurred while generating trip plan', 'alternatives': ['Please try again later', 'Contact support if the issue persists']},
                    'food': ['Error generating recommendations'],
                    'tips': f'Error: {e}'
                }
            }
