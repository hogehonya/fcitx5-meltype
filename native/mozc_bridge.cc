// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Yukishiro.
// Adapted from Meltype native/mozc/meltype_mozc_helper.cc. See ../NOTICE.
#include "mozc_bridge.h"
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <memory>
#include <string>
#include "base/system_util.h"
#include "composer/composer.h"
#include "config/config_handler.h"
#include "converter/converter_interface.h"
#include "converter/segments.h"
#include "data_manager/oss/oss_data_manager.h"
#include "engine/engine.h"
#include "protocol/commands.pb.h"
#include "request/conversion_request.h"
namespace {
class Bridge {
 public:
  explicit Bridge(std::unique_ptr<mozc::Engine> engine)
      : engine_(std::move(engine)), config_(mozc::config::ConfigHandler::DefaultConfig()),
        converter_(engine_->GetConverter()), composer_(request_, config_) {}
  bool Convert(const char* reading, const char* context, mozc::Segments* segments) {
    if (!reading || !*reading) return false;
    if (context && *context) (void)converter_->ReconstructHistory(segments, context);
    composer_.Reset();
    composer_.SetPreeditTextForTestOnly(reading);
    mozc::ConversionRequest::Options options = {
      .request_type = mozc::ConversionRequest::CONVERSION,
      .max_conversion_candidates_size = 100,
      .create_partial_candidates = false,
    };
    auto request = mozc::ConversionRequestBuilder().SetComposer(composer_)
      .SetRequestView(request_).SetConfigView(config_).SetOptions(std::move(options)).Build();
    return converter_->StartConversion(request, segments);
  }
  bool Predict(const char* reading, mozc::Segments* segments) {
    if (!reading || !*reading) return false;
    composer_.Reset();
    composer_.SetPreeditTextForTestOnly(reading);
    mozc::ConversionRequest::Options options = {
      .request_type = mozc::ConversionRequest::PREDICTION,
      .max_dictionary_prediction_candidates_size = 20,
      .create_partial_candidates = false,
    };
    auto request = mozc::ConversionRequestBuilder().SetComposer(composer_)
      .SetRequestView(request_).SetConfigView(config_).SetOptions(std::move(options)).Build();
    return converter_->StartPrediction(request, segments);
  }
 private:
  std::unique_ptr<mozc::Engine> engine_;
  const mozc::commands::Request request_;
  const mozc::config::Config config_;
  std::shared_ptr<const mozc::ConverterInterface> converter_;
  mozc::composer::Composer composer_;
};
std::unique_ptr<Bridge> bridge;
std::string profile;
char* Copy(const std::string& text) {
  if (text.empty()) return nullptr;
  auto* result = static_cast<char*>(std::malloc(text.size()+1));
  if (result) std::memcpy(result, text.c_str(), text.size()+1);
  return result;
}
}
extern "C" int meltype_mozc_bridge_init(const char* path) {
  try {
    if (!path || !*path || !std::filesystem::path(path).is_absolute()) return 0;
    if (bridge) return profile == path ? 1 : 0;
    std::filesystem::create_directories(path);
    mozc::SystemUtil::SetUserProfileDirectory(path);
    auto engine = mozc::Engine::CreateEngine(std::make_unique<mozc::oss::OssDataManager>());
    if (!engine.ok()) return 0;
    bridge = std::make_unique<Bridge>(std::move(engine.value()));
    profile = path;
    return 1;
  } catch (...) { return 0; }
}
extern "C" void meltype_mozc_bridge_shutdown() {
  try { bridge.reset(); profile.clear(); } catch (...) {}
}
extern "C" char* meltype_mozc_clauses(const char* reading, const char* context) {
  try {
    mozc::Segments segments;
    if (!bridge || !bridge->Convert(reading, context, &segments)) return nullptr;
    std::string text;
    for (size_t i=0; i<segments.conversion_segments_size(); ++i) {
      const auto& segment=segments.conversion_segment(i);
      if (!segment.candidates_size()) return nullptr;
      if (!text.empty()) text+='\n';
      text+=segment.key(); text+='\t'; text+=segment.candidate(0).value;
    }
    return Copy(text);
  } catch (...) { return nullptr; }
}
extern "C" char* meltype_mozc_candidates(const char* reading) {
  try {
    mozc::Segments segments;
    if (!bridge || !bridge->Convert(reading, nullptr, &segments)) return nullptr;
    std::string text;
    // Match the existing helper adapter: concatenate first candidates if Mozc
    // splits the reading, never return candidates for only part of the reading.
    if (segments.conversion_segments_size()!=1) {
      for (size_t i=0; i<segments.conversion_segments_size(); ++i) {
        const auto& part=segments.conversion_segment(i);
        if (!part.candidates_size()) return nullptr;
        text+=part.candidate(0).value;
      }
      return Copy(text);
    }
    const auto& segment=segments.conversion_segment(0);
    for (size_t i=0; i<segment.candidates_size(); ++i) {
      if (!text.empty()) text+='\n';
      text+=segment.candidate(i).value;
    }
    return Copy(text);
  } catch (...) { return nullptr; }
}

extern "C" char* meltype_mozc_predictions(const char* reading) {
  try {
    mozc::Segments segments;
    if (!bridge || !bridge->Predict(reading, &segments) || segments.conversion_segments_size()!=1) return nullptr;
    const auto& segment=segments.conversion_segment(0);
    std::string text;
    for (size_t i=0; i<segment.candidates_size() && i<20; ++i) {
      if (segment.candidate(i).value.empty()) continue;
      if (!text.empty()) text+='\n';
      text+=segment.candidate(i).value;
    }
    return Copy(text);
  } catch (...) { return nullptr; }
}
