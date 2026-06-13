# Cold storage compression utility for OpenF1 Bronze layer data
import os
import tarfile


def compress_bronze_layer() -> None:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data"))
    bronze_dir = os.path.join(base_dir, "bronze")
    archive_dir = os.path.join(bronze_dir, "archive")

    if not os.path.exists(bronze_dir):
        print("Diretório Bronze não existe. Operação abortada.")
        return

    print(f"Iniciando compressão fria da camada Bronze em: {bronze_dir}")

    # Varre subpastas recursivamente sob data/bronze/
    # Ignora a pasta data/bronze/archive/
    for root, dirs, files in os.walk(bronze_dir):
        if "archive" in root:
            continue

        json_files = [f for f in files if f.endswith(".json")]
        if not json_files:
            continue

        # Determina o caminho relativo correspondente
        rel_path = os.path.relpath(root, bronze_dir)
        print(f"Processando partição: {rel_path} ({len(json_files)} arquivos)")

        # Cria o diretório de histórico correspondente
        target_archive_dir = os.path.join(archive_dir, rel_path)
        os.makedirs(target_archive_dir, exist_ok=True)

        archive_name = os.path.join(target_archive_dir, "raw_data.tar.gz")

        # Cria o arquivo .tar.gz
        try:
            with tarfile.open(archive_name, "w:gz") as tar:
                for json_file in json_files:
                    full_json_path = os.path.join(root, json_file)
                    tar.add(full_json_path, arcname=json_file)

            # Deleta os JSONs originais de forma segura após compactação concluída
            for json_file in json_files:
                os.remove(os.path.join(root, json_file))

            print(
                f"Partição {rel_path} arquivada e compactada com sucesso em: {archive_name}"
            )
        except Exception as e:
            print(f"Erro ao compactar partição {rel_path}: {str(e)}")


if __name__ == "__main__":
    compress_bronze_layer()
