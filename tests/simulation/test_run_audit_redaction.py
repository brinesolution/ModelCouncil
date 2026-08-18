from simulation.audit.redaction import redact_audit_value


def test_recursive_redaction_removes_common_secret_fields_case_insensitively():
    payload = {
        "Authorization": "Bearer live-secret",
        "api_key": "key-123",
        "nested": {
            "APIKEY": "key-456",
            "access_token": "access-1",
            "refresh_token": "refresh-1",
            "password": "pw",
            "client_secret": "client-secret",
            "normal": "keep-me",
        },
        "items": [{"token": "nested-token", "value": 42}],
    }

    result = redact_audit_value(payload)

    assert result["Authorization"] == "[REDACTED]"
    assert result["api_key"] == "[REDACTED]"
    assert result["nested"]["APIKEY"] == "[REDACTED]"
    assert result["nested"]["access_token"] == "[REDACTED]"
    assert result["nested"]["refresh_token"] == "[REDACTED]"
    assert result["nested"]["password"] == "[REDACTED]"
    assert result["nested"]["client_secret"] == "[REDACTED]"
    assert result["items"][0]["token"] == "[REDACTED]"
    assert result["nested"]["normal"] == "keep-me"
    assert result["items"][0]["value"] == 42


def test_private_reasoning_fields_are_omitted_but_visible_content_is_kept():
    payload = {
        "message": {
            "content": "Visible assistant answer",
            "reasoning_content": "private reasoning text",
            "chain_of_thought": "private chain",
            "hidden_reasoning": "private hidden reasoning",
        }
    }

    result = redact_audit_value(payload)

    assert result["message"]["content"] == "Visible assistant answer"
    assert result["message"]["reasoning_content"] == "[OMITTED_PRIVATE_REASONING]"
    assert result["message"]["chain_of_thought"] == "[OMITTED_PRIVATE_REASONING]"
    assert result["message"]["hidden_reasoning"] == "[OMITTED_PRIVATE_REASONING]"
    serialized = str(result)
    assert "private reasoning text" not in serialized
    assert "private chain" not in serialized


def test_ollama_thinking_field_is_omitted_as_private_reasoning():
    payload = {
        "model": "qwen3:0.6b",
        "message": {
            "role": "assistant",
            "content": "Visible assistant answer",
            "thinking": "ollama private reasoning must never persist",
        },
    }

    result = redact_audit_value(payload)

    assert result["message"]["content"] == "Visible assistant answer"
    assert result["message"]["thinking"] == "[OMITTED_PRIVATE_REASONING]"
    assert "ollama private reasoning must never persist" not in str(result)
