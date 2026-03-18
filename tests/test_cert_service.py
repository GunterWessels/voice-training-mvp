def test_cert_issued_when_all_gates_pass():
    from backend.cert_service import should_issue_cert
    assert should_issue_cert(cof_clinical=True, cof_operational=True,
                              cof_financial=True, arc_stage=5, preset="full_practice") is True

def test_cert_not_issued_when_gate_missing():
    from backend.cert_service import should_issue_cert
    assert should_issue_cert(cof_clinical=True, cof_operational=False,
                              cof_financial=True, arc_stage=5, preset="full_practice") is False

def test_cert_not_issued_for_quick_drill():
    from backend.cert_service import should_issue_cert
    assert should_issue_cert(cof_clinical=True, cof_operational=True,
                              cof_financial=True, arc_stage=5, preset="quick_drill") is False

def test_cert_not_issued_below_arc_stage_5():
    from backend.cert_service import should_issue_cert
    assert should_issue_cert(cof_clinical=True, cof_operational=True,
                              cof_financial=True, arc_stage=4, preset="full_practice") is False

def test_pdf_generation_produces_file(tmp_path):
    from backend.cert_service import generate_cert_pdf
    completion_data = {
        "completion_id": "test-uuid-123",
        "rep_name": "Sarah Johnson",
        "scenario_name": "Tria Stents VAC Scenario",
        "completed_at": "2026-03-18",
        "score": 87,
        "cof_clinical": True,
        "cof_operational": True,
        "cof_financial": True,
    }
    output_path = tmp_path / "cert.pdf"
    generate_cert_pdf(completion_data, str(output_path))
    assert output_path.exists()
    assert output_path.stat().st_size > 1000  # Not empty
