# Email Classifier App

This project is a web application designed to automate the classification of emails into two categories: **Produtivo** (productive) and **Improdutivo** (unproductive). The application utilizes natural language processing (NLP) techniques and AI to analyze email content and suggest appropriate responses.

## Features

- Upload emails in `.txt` or `.pdf` format or paste email text directly.
- Automatic classification of emails into productive or unproductive categories.
- Suggested automatic responses based on the classification.
- User-friendly web interface for easy interaction.

## Project Structure

```
email-classifier-app
├── app
│   ├── __init__.py
│   ├── main.py
│   ├── routes.py
│   ├── nlp
│   │   ├── __init__.py
│   │   ├── preprocess.py
│   │   └── classifier.py
│   ├── ai
│   │   ├── __init__.py
│   │   └── client.py
│   ├── utils
│   │   ├── __init__.py
│   │   └── pdf_parser.py
│   ├── templates
│   │   ├── index.html
│   │   └── result.html
│   └── static
│       ├── css
│       │   └── styles.css
│       └── js
│           └── main.js
├── tests
│   ├── test_preprocess.py
│   └── test_classifier.py
├── sample_emails
│   ├── productive_example.txt
│   └── unproductive_example.txt
├── Dockerfile
├── Procfile
├── requirements.txt
├── .gitignore
└── README.md
```

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd email-classifier-app
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   python app/main.py

   or

   flask run
   ```

## Usage

- Navigate to `http://localhost:5000` in your web browser.
- Use the upload form to submit emails for classification.
- View the classification results and suggested responses on the results page.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for details.
