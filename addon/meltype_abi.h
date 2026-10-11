// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Yukishiro
// Adapted from upstream Meltype; see ../NOTICE.
#pragma once
// UTF-8 NUL terminated strings. Results belong to core; release with meltype_free.
// Calls and session lifetime are confined to the Fcitx event thread.
extern "C" {
int meltype_init(char *(*clauses)(const char *, const char *), char *(*candidates)(const char *), int (*is_word)(const char *));
void meltype_set_prediction_callback(char *(*predictions)(const char *, const char *));
int meltype_init_mozc(const char *helper, const char *profile);
int meltype_set_data_directory(const char *absolute_path);
void *meltype_create();
void meltype_destroy(void *session);
char *meltype_handle_key(void *session, int vk, int ch, int modifiers, const char *before, const char *after);
char *meltype_commit(void *session);
char *meltype_select_candidate(void *session, int index);
void meltype_free(void *result);
}
