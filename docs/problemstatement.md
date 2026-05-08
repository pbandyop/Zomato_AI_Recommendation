# Problem Statement: AI-Powered Restaurant Recommendation System (Zomato Use Case)

Build an intelligent restaurant recommendation application inspired by Zomato. The system should combine structured restaurant data with a Large Language Model (LLM) to generate personalized, explainable recommendations based on user preferences.

## Objective

Design and implement an application that:

- Accepts user preferences such as location, budget, cuisine, and minimum rating
- Uses a real-world restaurant dataset
- Leverages an LLM to produce personalized, natural-language recommendations
- Presents clear, useful, and easy-to-compare results

## System Workflow

### 1) Data Ingestion

- Load and preprocess the Zomato dataset from Hugging Face: [ManikaSaini/zomato-restaurant-recommendation](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation)
- Extract key fields such as restaurant name, location, cuisine, price range/cost, rating, and other relevant attributes

### 2) User Input Collection

Collect the following user preferences:

- **Location** (for example: Delhi, Bangalore)
- **Budget** (low, medium, high)
- **Cuisine** (for example: Italian, Chinese, North Indian)
- **Minimum rating**
- **Additional preferences** (optional, such as family-friendly, quick service, or ambience)

### 3) Integration Layer

- Filter and prepare candidate restaurants based on user constraints
- Convert filtered results into structured context for the LLM
- Design prompts that help the model reason, compare, and rank restaurant options accurately

### 4) Recommendation Engine

Use the LLM to:

- Rank the best matching restaurants
- Explain why each recommendation fits the user's preferences
- Optionally provide a short overall summary of top choices

### 5) Output Presentation

Display top recommendations in a user-friendly format with:

- Restaurant name
- Cuisine
- Rating
- Estimated cost
- AI-generated explanation

## Expected Outcome

The final system should deliver relevant, personalized, and transparent restaurant suggestions that make decision-making easier for users.
