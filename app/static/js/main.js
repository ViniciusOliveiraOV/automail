document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('upload-form');
    const resultDiv = document.getElementById('result');

    uploadForm.addEventListener('submit', function(event) {
        event.preventDefault();
        
        const formData = new FormData(uploadForm);
        
        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            resultDiv.innerHTML = `
                <h3>Resultado da Classificação:</h3>
                <p><strong>Categoria:</strong> ${data.category}</p>
                <p><strong>Resposta Sugerida:</strong> ${data.suggested_response}</p>
            `;
        })
        .catch(error => {
            console.error('Erro:', error);
            resultDiv.innerHTML = '<p>Ocorreu um erro ao processar o email.</p>';
        });
    });
});