from sunat_bot.__main__ import main


def test_resumen_falla_sin_credenciales_de_correo(tmp_path, monkeypatch, capsys):
    for k in ("SUNAT_IMAP_USUARIO", "SUNAT_IMAP_CLAVE"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("SUNAT_SALIDA", str(tmp_path))
    assert main(["--env", str(tmp_path / "no.env"), "resumen"]) == 2
    assert "Falta SUNAT_IMAP" in capsys.readouterr().err
    assert main(["--env", str(tmp_path / "no.env"), "resumen", "--sin-correo"]) == 0
