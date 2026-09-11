"use client";

import React, { useState, useRef, useCallback, useEffect } from "react";
import {
  UploadCloud,
  FileSpreadsheet,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  Play,
  Pause,
  RotateCcw,
  Download,
  Search,
  ArrowRight,
  ExternalLink,
  Layers,
  Sparkles,
  Check,
  Copy,
  Clock,
  Zap,
} from "lucide-react";
import {
  generateBulkAddresses,
  generateSampleCsvContent,
  GeneratedPostalRecord,
} from "@/app/lib/dataset-generator";

export interface BatchItemResult {
  id: string;
  raw_address: string;
  normalized_address: string;
  detected_language: string;
  confidence_score: number;
  conflict_flags: string[];
  extracted_entities: {
    locality: string;
    landmark: string;
    pin: string;
    city: string;
    state: string;
  };
  top_candidate: {
    id: string;
    office_name: string;
    pin_code: string;
    district: string;
    state: string;
    score: number;
  } | null;
  routing: {
    hub_code: string;
    delivery_beat: string;
    status: string;
  };
}

interface BatchDatasetProcessorProps {
  onInspectInStudio: (address: string) => void;
}

export default function BatchDatasetProcessor({ onInspectInStudio }: BatchDatasetProcessorProps) {
  const [itemsToProcess, setItemsToProcess] = useState<string[]>([]);
  const [results, setResults] = useState<BatchItemResult[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [progress, setProgress] = useState(0);
  const [processedCount, setProcessedCount] = useState(0);
  const [startTime, setStartTime] = useState<number | null>(null);
  const [elapsedSec, setElapsedSec] = useState(0);
  const [speedPerSec, setSpeedPerSec] = useState(0);

  // Filter & Search
  const [statusFilter, setStatusFilter] = useState<"ALL" | "RESOLVED" | "CONFLICTS" | "REVIEW">("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 25;

  // File dropzone state
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);
  const [uploadedFileSize, setUploadedFileSize] = useState<string | null>(null);
  const [pastedText, setPastedText] = useState("");
  const [showPasteModal, setShowPasteModal] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Active cancellation ref
  const cancelProcessingRef = useRef(false);

  // Timer for elapsed seconds
  useEffect(() => {
    let interval: any = null;
    if (isProcessing && !isPaused && startTime) {
      interval = setInterval(() => {
        const sec = Math.floor((Date.now() - startTime) / 1000);
        setElapsedSec(sec);
      }, 500);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isProcessing, isPaused, startTime]);

  // Load bulk items from text or CSV
  const parseAndLoadText = useCallback((text: string, filename?: string, sizeBytes?: number) => {
    const lines = text
      .split(/\r?\n/)
      .map((l) => l.trim())
      .filter((l) => l.length > 0);

    if (lines.length === 0) return;

    // Check if first line is CSV header
    const firstLine = lines[0].toLowerCase();
    let parsedAddresses: string[] = [];

    if (firstLine.includes(",") || firstLine.includes("address") || firstLine.includes("pin")) {
      // CSV format
      const headerCols = lines[0].split(",").map((h) => h.replace(/["']/g, "").trim().toLowerCase());
      const addrColIdx = headerCols.findIndex(
        (c) => c.includes("address") || c.includes("destination") || c.includes("street") || c.includes("raw")
      );

      const dataRows = lines.slice(1);
      parsedAddresses = dataRows
        .map((row) => {
          // Simple CSV splitter respecting quotes
          const parts = row.match(/(".*?"|[^",\s]+)(?=\s*,|\s*$)/g) || row.split(",");
          if (addrColIdx !== -1 && parts[addrColIdx]) {
            return parts[addrColIdx].replace(/^"|"$/g, "").trim();
          }
          return row.replace(/^"|"$/g, "").trim();
        })
        .filter((a) => a.length > 3);
    } else {
      // Line by line plain text
      parsedAddresses = lines.filter((l) => l.length > 3);
    }

    if (parsedAddresses.length > 0) {
      setItemsToProcess(parsedAddresses);
      setResults([]);
      setProgress(0);
      setProcessedCount(0);
      setUploadedFileName(filename || `dataset_${parsedAddresses.length}_items.csv`);
      if (sizeBytes) {
        const kb = Math.round(sizeBytes / 1024);
        setUploadedFileSize(kb > 1024 ? `${(kb / 1024).toFixed(1)} MB` : `${kb} KB`);
      } else {
        setUploadedFileSize(`${Math.round(text.length / 1024)} KB`);
      }
      setCurrentPage(1);
    }
  }, []);

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      const reader = new FileReader();
      reader.onload = (ev) => {
        const content = ev.target?.result as string;
        parseAndLoadText(content, file.name, file.size);
      };
      reader.readAsText(file);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      const reader = new FileReader();
      reader.onload = (ev) => {
        const content = ev.target?.result as string;
        parseAndLoadText(content, file.name, file.size);
      };
      reader.readAsText(file);
    }
  };

  // Pre-set bulk generator buttons
  const handleLoadGenerator = (count: number) => {
    const generated = generateBulkAddresses(count);
    const addresses = generated.map((g) => g.raw_address);
    setItemsToProcess(addresses);
    setResults([]);
    setProgress(0);
    setProcessedCount(0);
    setUploadedFileName(`nationwide_bulk_batch_${count}_records.csv`);
    setUploadedFileSize(`~${Math.round(count * 0.12)} KB`);
    setCurrentPage(1);
  };

  // Run the batch processing
  const startBatchExecution = async () => {
    if (itemsToProcess.length === 0 || isProcessing) return;

    setIsProcessing(true);
    setIsPaused(false);
    cancelProcessingRef.current = false;
    const start = Date.now();
    setStartTime(start);

    const CHUNK_SIZE = 50;
    const total = itemsToProcess.length;
    let accumulatedResults: BatchItemResult[] = [];

    for (let i = 0; i < total; i += CHUNK_SIZE) {
      if (cancelProcessingRef.current) break;

      const chunk = itemsToProcess.slice(i, i + CHUNK_SIZE);
      try {
        const res = await fetch("/api/v1/post-offices/batch", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ addresses: chunk }),
        });

        if (res.ok) {
          const data = await res.json();
          if (data.results) {
            accumulatedResults = [...accumulatedResults, ...data.results];
          }
        }
      } catch (err) {
        console.error("Batch chunk error:", err);
      }

      const currentDone = Math.min(i + CHUNK_SIZE, total);
      setProcessedCount(currentDone);
      setResults([...accumulatedResults]);
      setProgress(Math.round((currentDone / total) * 100));

      const elapsed = (Date.now() - start) / 1000;
      if (elapsed > 0) {
        setSpeedPerSec(Math.round(currentDone / elapsed));
      }

      // Small tick to yield to UI render loop
      await new Promise((resolve) => setTimeout(resolve, 15));
    }

    setIsProcessing(false);
  };

  const handlePauseToggle = () => {
    setIsPaused(!isPaused);
  };

  const handleCancel = () => {
    cancelProcessingRef.current = true;
    setIsProcessing(false);
  };

  const handleClear = () => {
    cancelProcessingRef.current = true;
    setIsProcessing(false);
    setItemsToProcess([]);
    setResults([]);
    setProgress(0);
    setProcessedCount(0);
    setUploadedFileName(null);
    setUploadedFileSize(null);
  };

  // Export Results
  const exportCsv = () => {
    if (results.length === 0) return;
    const headers = [
      "Record_ID",
      "Raw_Address",
      "Resolved_Post_Office",
      "Resolved_PIN",
      "District",
      "State",
      "Confidence_Score",
      "Sorting_Hub",
      "Delivery_Beat",
      "Conflict_Flags",
      "Processing_Status",
    ];

    const rows = results.map((r) => {
      const flags = (r.conflict_flags || []).join(" | ").replace(/"/g, '""');
      return [
        r.id,
        `"${r.raw_address.replace(/"/g, '""')}"`,
        `"${r.top_candidate?.office_name || "Unresolved"}"`,
        `"${r.top_candidate?.pin_code || ""}"`,
        `"${r.top_candidate?.district || ""}"`,
        `"${r.top_candidate?.state || ""}"`,
        r.confidence_score,
        `"${r.routing?.hub_code || ""}"`,
        `"${r.routing?.delivery_beat || ""}"`,
        `"${flags}"`,
        `"${r.routing?.status || ""}"`,
      ].join(",");
    });

    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `enriched_postal_dataset_${results.length}_records.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const exportJson = () => {
    if (results.length === 0) return;
    const jsonStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(results, null, 2));
    const link = document.createElement("a");
    link.setAttribute("href", jsonStr);
    link.setAttribute("download", `enriched_postal_dataset_${results.length}_records.json`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Metrics
  const totalCount = itemsToProcess.length;
  const resolvedCount = results.filter((r) => r.confidence_score >= 80 && r.conflict_flags.length === 0).length;
  const conflictCount = results.filter((r) => r.conflict_flags.length > 0).length;
  const reviewCount = results.filter((r) => r.confidence_score < 80 && r.conflict_flags.length === 0).length;

  // Filtered results
  const filteredResults = results.filter((r) => {
    if (statusFilter === "RESOLVED" && (r.confidence_score < 80 || r.conflict_flags.length > 0)) return false;
    if (statusFilter === "CONFLICTS" && r.conflict_flags.length === 0) return false;
    if (statusFilter === "REVIEW" && (r.confidence_score >= 80 || r.conflict_flags.length > 0)) return false;

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return (
        r.raw_address.toLowerCase().includes(q) ||
        (r.top_candidate?.office_name || "").toLowerCase().includes(q) ||
        (r.top_candidate?.pin_code || "").includes(q) ||
        (r.top_candidate?.district || "").toLowerCase().includes(q)
      );
    }
    return true;
  });

  // Pagination
  const totalPages = Math.ceil(filteredResults.length / itemsPerPage) || 1;
  const paginatedRows = filteredResults.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  return (
    <div
      style={{
        background: "rgba(15, 23, 42, 0.4)",
        border: "1px solid var(--glass-border-subtle)",
        borderRadius: "14px",
        padding: "24px",
        marginTop: "16px",
      }}
    >
      {/* Header & Description */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "12px", marginBottom: "20px" }}>
        <div>
          <h3 style={{ fontSize: "18px", fontWeight: 800, display: "flex", alignItems: "center", gap: "8px" }}>
            <FileSpreadsheet size={20} color="var(--accent-saffron)" /> Enterprise Huge Dataset Batch Processor
          </h3>
          <p style={{ fontSize: "13px", color: "var(--text-muted)", marginTop: "4px" }}>
            Batch verify, standardize, and route thousands of Indian postal addresses, parcels, and e-commerce consignments in seconds.
          </p>
        </div>

        {/* Action Controls if Dataset Loaded */}
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          {itemsToProcess.length > 0 && !isProcessing && (
            <button
              onClick={startBatchExecution}
              style={{
                background: "var(--accent-saffron)",
                color: "#000",
                border: "none",
                borderRadius: "8px",
                padding: "8px 16px",
                fontSize: "12px",
                fontWeight: 800,
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
              }}
            >
              <Play size={14} fill="#000" /> Start Processing {itemsToProcess.length} Items
            </button>
          )}

          {isProcessing && (
            <button
              onClick={handleCancel}
              style={{
                background: "rgba(239, 68, 68, 0.2)",
                color: "#f87171",
                border: "1px solid rgba(239, 68, 68, 0.4)",
                borderRadius: "8px",
                padding: "8px 14px",
                fontSize: "12px",
                fontWeight: 700,
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
              }}
            >
              Cancel Batch Run
            </button>
          )}

          {results.length > 0 && (
            <>
              <button
                onClick={exportCsv}
                style={{
                  background: "rgba(16, 185, 129, 0.15)",
                  color: "var(--accent-emerald)",
                  border: "1px solid rgba(16, 185, 129, 0.35)",
                  borderRadius: "8px",
                  padding: "8px 14px",
                  fontSize: "12px",
                  fontWeight: 700,
                  cursor: "pointer",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                }}
              >
                <Download size={14} /> Export Enriched CSV
              </button>
              <button
                onClick={exportJson}
                style={{
                  background: "rgba(255, 255, 255, 0.05)",
                  color: "var(--text-main)",
                  border: "1px solid var(--glass-border-subtle)",
                  borderRadius: "8px",
                  padding: "8px 14px",
                  fontSize: "12px",
                  fontWeight: 700,
                  cursor: "pointer",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                }}
              >
                Export JSON
              </button>
              <button
                onClick={handleClear}
                style={{
                  background: "transparent",
                  color: "var(--text-muted)",
                  border: "none",
                  padding: "8px 10px",
                  fontSize: "12px",
                  cursor: "pointer",
                }}
              >
                Clear
              </button>
            </>
          )}
        </div>
      </div>

      {/* Hidden File Input */}
      <input
        type="file"
        ref={fileInputRef}
        accept=".csv,.tsv,.json,.txt"
        style={{ display: "none" }}
        onChange={handleFileSelect}
      />

      {/* Dropzone & Loaders when no items or wanting to reload */}
      {itemsToProcess.length === 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "1.2fr 0.8fr", gap: "20px" }}>
          {/* Left: Drag & Drop Zone */}
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragOver(true);
            }}
            onDragLeave={() => setIsDragOver(false)}
            onDrop={handleFileDrop}
            onClick={() => fileInputRef.current?.click()}
            style={{
              border: isDragOver ? "2px dashed var(--accent-emerald)" : "2px dashed var(--accent-saffron)",
              borderRadius: "12px",
              padding: "36px 20px",
              textAlign: "center",
              background: isDragOver ? "rgba(16, 185, 129, 0.08)" : "rgba(245, 158, 11, 0.04)",
              cursor: "pointer",
              transition: "all 0.2s ease",
            }}
          >
            <UploadCloud
              size={42}
              color={isDragOver ? "var(--accent-emerald)" : "var(--accent-saffron)"}
              style={{ margin: "0 auto 12px" }}
            />
            <h4 style={{ fontSize: "16px", fontWeight: 800 }}>
              Drop Your Huge Address Dataset (CSV, JSON, TSV, TXT)
            </h4>
            <p style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "6px", maxWidth: "420px", margin: "6px auto 0" }}>
              Supports thousands of lines with automatic address column detection, missing PIN inference, and delivery post office resolution.
            </p>
            <div style={{ marginTop: "16px", display: "inline-block" }}>
              <span
                style={{
                  background: "rgba(255,255,255,0.08)",
                  padding: "6px 14px",
                  borderRadius: "20px",
                  fontSize: "11px",
                  fontWeight: 700,
                  color: "var(--accent-saffron)",
                }}
              >
                Browse Files from Device
              </span>
            </div>
          </div>

          {/* Right: Quick Generators & Templates */}
          <div
            style={{
              background: "rgba(255, 255, 255, 0.02)",
              border: "1px solid var(--glass-border-subtle)",
              borderRadius: "12px",
              padding: "20px",
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
            }}
          >
            <div>
              <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-muted)", fontFamily: "JetBrains Mono" }}>
                BENCHMARK WITH ENTERPRISE DATASETS:
              </span>
              <p style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "4px" }}>
                Instantly load synthetic real-world consignment batches with intentional typos, PIN conflicts, and multi-circle addresses:
              </p>

              <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginTop: "14px" }}>
                <button
                  onClick={() => handleLoadGenerator(100)}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "10px 14px",
                    background: "rgba(255, 255, 255, 0.04)",
                    border: "1px solid var(--glass-border-subtle)",
                    borderRadius: "8px",
                    color: "var(--text-main)",
                    cursor: "pointer",
                    textAlign: "left",
                  }}
                >
                  <div>
                    <div style={{ fontSize: "12px", fontWeight: 700 }}>⚡ Load 100 Sample Addresses Batch</div>
                    <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>Chennai, Delhi, Mumbai, Bengaluru Metros</div>
                  </div>
                  <span style={{ fontSize: "11px", color: "var(--accent-saffron)", fontWeight: 700 }}>100 rows</span>
                </button>

                <button
                  onClick={() => handleLoadGenerator(500)}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "10px 14px",
                    background: "rgba(255, 255, 255, 0.04)",
                    border: "1px solid var(--glass-border-subtle)",
                    borderRadius: "8px",
                    color: "var(--text-main)",
                    cursor: "pointer",
                    textAlign: "left",
                  }}
                >
                  <div>
                    <div style={{ fontSize: "12px", fontWeight: 700 }}>🚀 Load 500 Nationwide Consignments</div>
                    <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>All 14 Postal Circles • High Typo Variance</div>
                  </div>
                  <span style={{ fontSize: "11px", color: "var(--accent-emerald)", fontWeight: 700 }}>500 rows</span>
                </button>

                <button
                  onClick={() => handleLoadGenerator(2000)}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "10px 14px",
                    background: "rgba(255, 255, 255, 0.04)",
                    border: "1px solid var(--glass-border-subtle)",
                    borderRadius: "8px",
                    color: "var(--text-main)",
                    cursor: "pointer",
                    textAlign: "left",
                  }}
                >
                  <div>
                    <div style={{ fontSize: "12px", fontWeight: 700 }}>🔥 Load 2,000 Huge Enterprise Dataset</div>
                    <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>Large e-commerce logistics stress test</div>
                  </div>
                  <span style={{ fontSize: "11px", color: "#60a5fa", fontWeight: 700 }}>2,000 rows</span>
                </button>
              </div>
            </div>

            <div style={{ marginTop: "16px", paddingTop: "12px", borderTop: "1px solid var(--glass-border-subtle)" }}>
              <button
                onClick={() => {
                  const csv = generateSampleCsvContent(20);
                  const encodedUri = encodeURI("data:text/csv;charset=utf-8," + csv);
                  const link = document.createElement("a");
                  link.setAttribute("href", encodedUri);
                  link.setAttribute("download", "sample_india_post_import_template.csv");
                  document.body.appendChild(link);
                  link.click();
                  document.body.removeChild(link);
                }}
                style={{
                  background: "transparent",
                  color: "var(--accent-saffron)",
                  border: "none",
                  fontSize: "11px",
                  fontWeight: 700,
                  cursor: "pointer",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "4px",
                }}
              >
                <Download size={12} /> Download Standard CSV Import Template
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Progress & Live KPIs when items are loaded */}
      {itemsToProcess.length > 0 && (
        <div>
          {/* File Meta Banner */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              background: "rgba(255, 255, 255, 0.03)",
              border: "1px solid var(--glass-border-subtle)",
              borderRadius: "10px",
              padding: "10px 16px",
              marginBottom: "16px",
              flexWrap: "wrap",
              gap: "10px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <FileSpreadsheet size={20} color="var(--accent-saffron)" />
              <div>
                <span style={{ fontSize: "13px", fontWeight: 800, color: "var(--text-main)" }}>
                  {uploadedFileName || "Active Postal Dataset"}
                </span>
                <span style={{ fontSize: "11px", color: "var(--text-muted)", marginLeft: "8px" }}>
                  {totalCount.toLocaleString()} total address records ({uploadedFileSize})
                </span>
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
              {isProcessing && (
                <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "var(--accent-emerald)" }}>
                  <Zap size={14} className="spin" /> Processing @ ~{speedPerSec} records/sec
                </div>
              )}
              {elapsedSec > 0 && (
                <div style={{ fontSize: "12px", color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "4px" }}>
                  <Clock size={13} /> {Math.floor(elapsedSec / 60)}m {elapsedSec % 60}s elapsed
                </div>
              )}
            </div>
          </div>

          {/* Animated Progress Bar */}
          <div style={{ marginBottom: "20px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", fontWeight: 700, color: "var(--text-muted)", marginBottom: "6px", fontFamily: "JetBrains Mono" }}>
              <span>BATCH PROGRESS: {processedCount.toLocaleString()} / {totalCount.toLocaleString()} COMPLETED</span>
              <span style={{ color: progress === 100 ? "var(--accent-emerald)" : "var(--accent-saffron)" }}>
                {progress}%
              </span>
            </div>
            <div
              style={{
                width: "100%",
                height: "8px",
                background: "rgba(255, 255, 255, 0.08)",
                borderRadius: "4px",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  width: `${progress}%`,
                  height: "100%",
                  background: progress === 100 ? "var(--accent-emerald)" : "linear-gradient(90deg, var(--accent-saffron), #60a5fa)",
                  transition: "width 0.15s ease",
                }}
              />
            </div>
          </div>

          {/* KPI Cards Grid */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "12px", marginBottom: "20px" }}>
            <div
              style={{
                background: "rgba(255, 255, 255, 0.03)",
                border: "1px solid var(--glass-border-subtle)",
                borderRadius: "10px",
                padding: "12px 16px",
              }}
            >
              <div style={{ fontSize: "10px", fontWeight: 700, color: "var(--text-muted)", fontFamily: "JetBrains Mono" }}>TOTAL SUBMITTED</div>
              <div style={{ fontSize: "20px", fontWeight: 800, marginTop: "4px" }}>{totalCount.toLocaleString()}</div>
            </div>

            <div
              style={{
                background: "rgba(16, 185, 129, 0.08)",
                border: "1px solid rgba(16, 185, 129, 0.3)",
                borderRadius: "10px",
                padding: "12px 16px",
              }}
            >
              <div style={{ fontSize: "10px", fontWeight: 700, color: "var(--accent-emerald)", fontFamily: "JetBrains Mono" }}>AUTO-RESOLVED (HIGH CONF)</div>
              <div style={{ fontSize: "20px", fontWeight: 800, color: "var(--accent-emerald)", marginTop: "4px" }}>
                {resolvedCount.toLocaleString()}{" "}
                <span style={{ fontSize: "12px", fontWeight: 400 }}>
                  ({results.length > 0 ? Math.round((resolvedCount / results.length) * 100) : 0}%)
                </span>
              </div>
            </div>

            <div
              style={{
                background: "rgba(245, 158, 11, 0.08)",
                border: "1px solid rgba(245, 158, 11, 0.3)",
                borderRadius: "10px",
                padding: "12px 16px",
              }}
            >
              <div style={{ fontSize: "10px", fontWeight: 700, color: "var(--accent-saffron)", fontFamily: "JetBrains Mono" }}>PIN CONFLICTS REROUTED</div>
              <div style={{ fontSize: "20px", fontWeight: 800, color: "var(--accent-saffron)", marginTop: "4px" }}>
                {conflictCount.toLocaleString()}{" "}
                <span style={{ fontSize: "12px", fontWeight: 400 }}>
                  ({results.length > 0 ? Math.round((conflictCount / results.length) * 100) : 0}%)
                </span>
              </div>
            </div>

            <div
              style={{
                background: "rgba(239, 68, 68, 0.08)",
                border: "1px solid rgba(239, 68, 68, 0.3)",
                borderRadius: "10px",
                padding: "12px 16px",
              }}
            >
              <div style={{ fontSize: "10px", fontWeight: 700, color: "#f87171", fontFamily: "JetBrains Mono" }}>MANUAL REVIEW REQUIRED</div>
              <div style={{ fontSize: "20px", fontWeight: 800, color: "#f87171", marginTop: "4px" }}>
                {reviewCount.toLocaleString()}{" "}
                <span style={{ fontSize: "12px", fontWeight: 400 }}>
                  ({results.length > 0 ? Math.round((reviewCount / results.length) * 100) : 0}%)
                </span>
              </div>
            </div>
          </div>

          {/* Results Table Controls */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px", marginBottom: "12px" }}>
            <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
              <button
                onClick={() => {
                  setStatusFilter("ALL");
                  setCurrentPage(1);
                }}
                style={{
                  fontSize: "11px",
                  fontWeight: 700,
                  padding: "5px 10px",
                  borderRadius: "6px",
                  border: statusFilter === "ALL" ? "1.5px solid var(--accent-saffron)" : "1px solid var(--glass-border-subtle)",
                  background: statusFilter === "ALL" ? "rgba(245, 158, 11, 0.12)" : "rgba(255,255,255,0.03)",
                  color: "inherit",
                  cursor: "pointer",
                }}
              >
                All Records ({results.length})
              </button>
              <button
                onClick={() => {
                  setStatusFilter("RESOLVED");
                  setCurrentPage(1);
                }}
                style={{
                  fontSize: "11px",
                  fontWeight: 700,
                  padding: "5px 10px",
                  borderRadius: "6px",
                  border: statusFilter === "RESOLVED" ? "1.5px solid var(--accent-emerald)" : "1px solid var(--glass-border-subtle)",
                  background: statusFilter === "RESOLVED" ? "rgba(16, 185, 129, 0.12)" : "rgba(255,255,255,0.03)",
                  color: "inherit",
                  cursor: "pointer",
                }}
              >
                Auto-Resolved ({resolvedCount})
              </button>
              <button
                onClick={() => {
                  setStatusFilter("CONFLICTS");
                  setCurrentPage(1);
                }}
                style={{
                  fontSize: "11px",
                  fontWeight: 700,
                  padding: "5px 10px",
                  borderRadius: "6px",
                  border: statusFilter === "CONFLICTS" ? "1.5px solid var(--accent-saffron)" : "1px solid var(--glass-border-subtle)",
                  background: statusFilter === "CONFLICTS" ? "rgba(245, 158, 11, 0.12)" : "rgba(255,255,255,0.03)",
                  color: "inherit",
                  cursor: "pointer",
                }}
              >
                PIN Conflicts / Rerouted ({conflictCount})
              </button>
              <button
                onClick={() => {
                  setStatusFilter("REVIEW");
                  setCurrentPage(1);
                }}
                style={{
                  fontSize: "11px",
                  fontWeight: 700,
                  padding: "5px 10px",
                  borderRadius: "6px",
                  border: statusFilter === "REVIEW" ? "1.5px solid #f87171" : "1px solid var(--glass-border-subtle)",
                  background: statusFilter === "REVIEW" ? "rgba(239, 68, 68, 0.12)" : "rgba(255,255,255,0.03)",
                  color: "inherit",
                  cursor: "pointer",
                }}
              >
                Needs Review ({reviewCount})
              </button>
            </div>

            {/* Search filter within results */}
            <div style={{ position: "relative", minWidth: "220px" }}>
              <Search size={13} style={{ position: "absolute", left: "10px", top: "9px", color: "var(--text-muted)" }} />
              <input
                type="text"
                placeholder="Search addresses, offices, PINs..."
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setCurrentPage(1);
                }}
                style={{
                  width: "100%",
                  padding: "6px 12px 6px 28px",
                  borderRadius: "6px",
                  border: "1px solid var(--glass-border-subtle)",
                  background: "rgba(255, 255, 255, 0.05)",
                  color: "var(--text-main)",
                  fontSize: "11px",
                }}
              />
            </div>
          </div>

          {/* Results Table */}
          <div
            style={{
              overflowX: "auto",
              background: "rgba(0,0,0,0.25)",
              borderRadius: "10px",
              border: "1px solid var(--glass-border-subtle)",
            }}
          >
            <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "12px" }}>
              <thead>
                <tr style={{ background: "rgba(255,255,255,0.04)", borderBottom: "1px solid var(--glass-border-subtle)" }}>
                  <th style={{ padding: "10px 12px", color: "var(--text-muted)", fontFamily: "JetBrains Mono", fontSize: "10px" }}>#</th>
                  <th style={{ padding: "10px 12px", color: "var(--text-muted)", fontFamily: "JetBrains Mono", fontSize: "10px" }}>RAW INPUT ADDRESS</th>
                  <th style={{ padding: "10px 12px", color: "var(--text-muted)", fontFamily: "JetBrains Mono", fontSize: "10px" }}>RESOLVED DELIVERY PO</th>
                  <th style={{ padding: "10px 12px", color: "var(--text-muted)", fontFamily: "JetBrains Mono", fontSize: "10px" }}>ASSIGNED PIN</th>
                  <th style={{ padding: "10px 12px", color: "var(--text-muted)", fontFamily: "JetBrains Mono", fontSize: "10px" }}>ROUTING HUB & BEAT</th>
                  <th style={{ padding: "10px 12px", color: "var(--text-muted)", fontFamily: "JetBrains Mono", fontSize: "10px" }}>CONFIDENCE</th>
                  <th style={{ padding: "10px 12px", color: "var(--text-muted)", fontFamily: "JetBrains Mono", fontSize: "10px" }}>STATUS</th>
                  <th style={{ padding: "10px 12px", color: "var(--text-muted)", fontFamily: "JetBrains Mono", fontSize: "10px" }}>ACTION</th>
                </tr>
              </thead>
              <tbody>
                {paginatedRows.length === 0 && (
                  <tr>
                    <td colSpan={8} style={{ padding: "32px", textAlign: "center", color: "var(--text-muted)" }}>
                      {isProcessing ? "Processing batch in chunks..." : "No records match the current filter."}
                    </td>
                  </tr>
                )}
                {paginatedRows.map((r, idx) => {
                  const hasConflict = r.conflict_flags.length > 0;
                  const rowNum = (currentPage - 1) * itemsPerPage + idx + 1;

                  return (
                    <tr
                      key={`${r.id}-${idx}`}
                      style={{
                        borderBottom: "1px solid rgba(255,255,255,0.04)",
                        background: hasConflict ? "rgba(245, 158, 11, 0.02)" : "transparent",
                      }}
                    >
                      <td style={{ padding: "10px 12px", fontFamily: "JetBrains Mono", color: "var(--text-muted)", fontSize: "11px" }}>
                        {rowNum}
                      </td>
                      <td style={{ padding: "10px 12px", maxWidth: "280px" }}>
                        <div style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", fontWeight: 600 }}>
                          {r.raw_address}
                        </div>
                        {hasConflict && (
                          <div style={{ fontSize: "10px", color: "var(--accent-saffron)", marginTop: "2px", display: "flex", alignItems: "center", gap: "4px" }}>
                            <AlertTriangle size={10} /> {r.conflict_flags[0]}
                          </div>
                        )}
                      </td>
                      <td style={{ padding: "10px 12px" }}>
                        <div style={{ fontWeight: 700, color: "var(--text-main)" }}>
                          {r.top_candidate?.office_name || "Unassigned"}
                        </div>
                        <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>
                          {r.top_candidate?.district}, {r.top_candidate?.state}
                        </div>
                      </td>
                      <td style={{ padding: "10px 12px" }}>
                        <span
                          style={{
                            fontFamily: "JetBrains Mono",
                            fontWeight: 700,
                            padding: "3px 8px",
                            borderRadius: "4px",
                            background: hasConflict ? "rgba(245, 158, 11, 0.2)" : "rgba(16, 185, 129, 0.2)",
                            color: hasConflict ? "var(--accent-saffron)" : "var(--accent-emerald)",
                          }}
                        >
                          {r.top_candidate?.pin_code || "N/A"}
                        </span>
                      </td>
                      <td style={{ padding: "10px 12px" }}>
                        <div style={{ fontSize: "11px", fontWeight: 600 }}>{r.routing?.hub_code || "NSH-MAA"}</div>
                        <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>{r.routing?.delivery_beat || "Beat #01"}</div>
                      </td>
                      <td style={{ padding: "10px 12px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                          <span
                            style={{
                              fontWeight: 800,
                              fontFamily: "JetBrains Mono",
                              color:
                                r.confidence_score >= 85
                                  ? "var(--accent-emerald)"
                                  : r.confidence_score >= 70
                                  ? "var(--accent-saffron)"
                                  : "#f87171",
                            }}
                          >
                            {r.confidence_score}%
                          </span>
                        </div>
                      </td>
                      <td style={{ padding: "10px 12px" }}>
                        <span
                          style={{
                            fontSize: "10px",
                            fontWeight: 700,
                            padding: "3px 8px",
                            borderRadius: "10px",
                            background:
                              r.confidence_score >= 80 && !hasConflict
                                ? "rgba(16, 185, 129, 0.2)"
                                : hasConflict
                                ? "rgba(245, 158, 11, 0.2)"
                                : "rgba(239, 68, 68, 0.2)",
                            color:
                              r.confidence_score >= 80 && !hasConflict
                                ? "var(--accent-emerald)"
                                : hasConflict
                                ? "var(--accent-saffron)"
                                : "#f87171",
                          }}
                        >
                          {r.confidence_score >= 80 && !hasConflict
                            ? "RESOLVED"
                            : hasConflict
                            ? "REROUTED"
                            : "NEEDS REVIEW"}
                        </span>
                      </td>
                      <td style={{ padding: "10px 12px" }}>
                        <button
                          onClick={() => onInspectInStudio(r.raw_address)}
                          style={{
                            background: "rgba(255,255,255,0.06)",
                            border: "1px solid var(--glass-border-subtle)",
                            color: "var(--text-main)",
                            borderRadius: "4px",
                            padding: "4px 8px",
                            fontSize: "10px",
                            cursor: "pointer",
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "4px",
                          }}
                        >
                          Inspect <ArrowRight size={11} />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "14px", fontSize: "11px", color: "var(--text-muted)" }}>
              <span>
                Showing {(currentPage - 1) * itemsPerPage + 1} to {Math.min(currentPage * itemsPerPage, filteredResults.length)} of {filteredResults.length} filtered items
              </span>
              <div style={{ display: "flex", gap: "6px" }}>
                <button
                  disabled={currentPage === 1}
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  style={{
                    padding: "4px 10px",
                    borderRadius: "4px",
                    border: "1px solid var(--glass-border-subtle)",
                    background: "rgba(255,255,255,0.05)",
                    color: "inherit",
                    cursor: currentPage === 1 ? "not-allowed" : "pointer",
                    opacity: currentPage === 1 ? 0.4 : 1,
                  }}
                >
                  Previous
                </button>
                <span style={{ padding: "4px 8px", fontWeight: 700, color: "var(--text-main)" }}>
                  Page {currentPage} of {totalPages}
                </span>
                <button
                  disabled={currentPage === totalPages}
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  style={{
                    padding: "4px 10px",
                    borderRadius: "4px",
                    border: "1px solid var(--glass-border-subtle)",
                    background: "rgba(255,255,255,0.05)",
                    color: "inherit",
                    cursor: currentPage === totalPages ? "not-allowed" : "pointer",
                    opacity: currentPage === totalPages ? 0.4 : 1,
                  }}
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
