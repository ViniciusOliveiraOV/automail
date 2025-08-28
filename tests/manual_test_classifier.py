from app.nlp.classifier import EmailClassifier

def main():
    clf = EmailClassifier()
    train_texts = [
        "Meu sistema apresentou um erro ao salvar o arquivo",
        "Obrigado pelo rápido retorno, ótimo trabalho"
    ]
    train_labels = ["Produtivo", "Improdutivo"]
    clf.train(train_texts, train_labels)
    print("Classify 1:", clf.classify("Há uma falha ao anexar documentos"))
    print("Classify 2:", clf.classify("Obrigado pela ajuda prestada"))
    clf.save_model("tests/test_model.pkl")

    # carregar e testar
    clf2 = EmailClassifier()
    clf2.load_model("tests/test_model.pkl")
    print("Loaded classify:", clf2.classify("Preciso de suporte, erro 500"))

if __name__ == '__main__':
    main()