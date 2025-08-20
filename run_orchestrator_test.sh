#!/bin/bash
#
# Script to run the complete orchestrator test
# 1. Checks for running agents
# 2. Launches all required agents  
# 3. Runs the orchestrator tests
# 4. Cleans up

set -e

echo "============================================"
echo "🚀 ORCHESTRATOR TEST RUNNER"
echo "============================================"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not found"
    exit 1
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping all agents..."
    pkill -f "keyword_agent.py" 2>/dev/null || true
    pkill -f "grep_agent.py" 2>/dev/null || true
    pkill -f "chunk_agent.py" 2>/dev/null || true
    pkill -f "summarize_agent.py" 2>/dev/null || true
    pkill -f "temporal_tagging_agent.py" 2>/dev/null || true
    pkill -f "encounter_grouping_agent.py" 2>/dev/null || true
    pkill -f "reconciliation_agent.py" 2>/dev/null || true
    pkill -f "summary_extractor_agent.py" 2>/dev/null || true
    pkill -f "timeline_builder_agent.py" 2>/dev/null || true
    pkill -f "checker_agent.py" 2>/dev/null || true
    pkill -f "unified_extractor_agent.py" 2>/dev/null || true
    pkill -f "unified_verifier_agent.py" 2>/dev/null || true
    pkill -f "narrative_synthesis_agent.py" 2>/dev/null || true
    pkill -f "orchestrator_agent.py" 2>/dev/null || true
    pkill -f "simple_orchestrator_agent.py" 2>/dev/null || true
    echo "✅ Cleanup complete"
}

# Set trap for cleanup on exit
trap cleanup EXIT INT TERM

# Step 1: Check for already running agents
echo "📍 Step 1: Checking for already running agents..."
if lsof -i:8002 &>/dev/null || lsof -i:8006 &>/dev/null || lsof -i:8008 &>/dev/null; then
    echo "⚠️  Some agents appear to be already running"
    echo "   Cleaning up old processes..."
    cleanup
    sleep 2
fi
echo "✅ Ports are clear"
echo ""

# Step 2: Launch all agents
echo "📍 Step 2: Launching all agents..."
echo "   This will start all pipeline agents and orchestrators"
echo ""

# Launch agents with full logging in background
export SHOW_AGENT_CALLS=true
export LOG_LEVEL=INFO
python3 launch_all_agents.py &
AGENT_PID=$!

# Wait for agents to be ready
echo "⏳ Waiting for agents to initialize (30 seconds)..."
sleep 30

# Check if agent launcher is still running
if ! ps -p $AGENT_PID > /dev/null; then
    echo "❌ Agent launcher failed to start agents"
    exit 1
fi

echo "✅ Agents should be running"
echo ""

# Step 3: Run the orchestrator tests
echo "📍 Step 3: Running orchestrator tests..."
echo ""
python3 test_orchestrators.py

echo ""
echo "============================================"
echo "✅ TEST COMPLETE"
echo "============================================"
echo ""
echo "Check orchestrator_test_results.json for detailed results"
echo ""