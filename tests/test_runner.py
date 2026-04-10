"""Tests for the benchmark runner."""

from __future__ import annotations

import pytest

from synthbench.runner import BenchmarkRunner


@pytest.mark.asyncio
async def test_runner_with_mock_provider(mock_dataset, mock_provider):
    """End-to-end: runner produces results with deterministic mock."""
    runner = BenchmarkRunner(
        dataset=mock_dataset,
        provider=mock_provider,
        samples_per_question=10,
        concurrency=5,
    )
    result = await runner.run(n=3)

    assert result.dataset_name == "mock"
    assert result.provider_name == "mock/deterministic"
    assert len(result.questions) == 3
    assert result.elapsed_seconds > 0

    for qr in result.questions:
        assert 0.0 <= qr.jsd <= 1.0
        assert -1.0 <= qr.kendall_tau <= 1.0
        assert 0.0 <= qr.parity <= 1.0
        assert qr.n_samples == 10
        # Deterministic provider always picks first option
        assert qr.model_distribution[qr.options[0]] == 1.0

    assert 0.0 <= result.composite_parity <= 1.0


@pytest.mark.asyncio
async def test_runner_with_random_provider(mock_dataset, random_provider):
    """Random provider produces varied distributions."""
    runner = BenchmarkRunner(
        dataset=mock_dataset,
        provider=random_provider,
        samples_per_question=100,
        concurrency=5,
    )
    result = await runner.run(n=2)

    assert len(result.questions) == 2
    for qr in result.questions:
        # Random should spread across options (not all on one)
        nonzero = sum(1 for v in qr.model_distribution.values() if v > 0)
        assert nonzero >= 2


@pytest.mark.asyncio
async def test_runner_n_limits_questions(mock_dataset, mock_provider):
    """--n flag limits the number of questions evaluated."""
    runner = BenchmarkRunner(
        dataset=mock_dataset,
        provider=mock_provider,
        samples_per_question=5,
    )
    result = await runner.run(n=1)
    assert len(result.questions) == 1


@pytest.mark.asyncio
async def test_runner_progress_callback(mock_dataset, mock_provider):
    """Progress callback is called for each question."""
    calls = []

    def cb(done, total, qr):
        calls.append((done, total))

    runner = BenchmarkRunner(
        dataset=mock_dataset,
        provider=mock_provider,
        samples_per_question=5,
    )
    await runner.run(n=3, progress_callback=cb)

    assert len(calls) == 3
    assert calls[-1] == (3, 3)
