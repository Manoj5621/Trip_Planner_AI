<img src="static/images/logos.png" alt="" align="center" width="225" height="150"><h1 align="center">Travelogue - AI</h1>
<p align="center"><a href="#project-description">Project Description</a> - <a href="#key-features">Key Features</a> - <a href="#technology-stack">Tech Stack</a></p>

<img src="static/images/landingpage.png" alt="" align="center" width="auto" height="auto">

## Project Description

AITrip Planner is a project built using the Django web framework. It follows the Model-View-Template (MVT) architecture where URLs route user requests to views, views handle business logic, and models interact with the database. The project uses forms to process and validate user input, while templates render HTML pages for the frontend. Static files like CSS, JavaScript, and images enhance the user interface. Middleware manages request and response processing, including user authentication. The project uses an SQLite database to securely store user and trip information. This architecture ensures the project is modular, maintainable, and scalable.

## Key Components

**Function to parse the AI response**

```

    def _parse_ai_response(self, response_text):  
        try: if isinstance(response_text, dict): return response_text

        response_text = response_text.strip()
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        if start_idx >= 0 and end_idx > start_idx:
            json_str = response_text[start_idx:end_idx]
            return json.loads(json_str)

        raise ValueError("Could not find valid JSON in response")

    except Exception as e:

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

```

## Key Features

**Multi-Provider AI Support** Supports OpenAI (GPT-4), Google Gemini, and Anthropic Claude, allowing flexible backend selection for generating trip plans.

**Smart Prompt Generation** Dynamically creates detailed prompts based on trip data, including dates, destination, number of people, and preferred activities.

**Structured JSON Output** Parses AI responses into a consistent JSON format with day-wise plans, including activities, food suggestions, and travel tips.

**Robust Error Handling** Includes error fallbacks, environment variable checks, and validation to ensure the system handles failures gracefully.

**Pluggable & Extensible Design** Built as a modular class, making it easy to extend or switch providers, customize prompts, or change response formatting.

## Tech Stack

**🔧 Technology Stack**

**Backend**

*   Django (Python)
    
*   Google Generative AI (Gemini)
    
*   OpenAI (GPT-4)
    
*   Anthropic (Claude 3)
    

**Frontend**

*   HTML
    
*   CSS
    
*   Bootstrap
    
*   JavaScript
    

**Database**

*   SQLite (via Django ORM)

**Authentication**

*   Django Built-in Authentication System
