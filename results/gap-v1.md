# Gap table: rubash vs gnu

ratio = rubash time / gnu time (per-op median). <1.00 = rubash faster.

- **leading** (ratio <= 0.98): 53
- **close** (0.98 < ratio <= 1.10): 17
- **behind** (ratio > 1.10): 338
- compared cases: 408, unmeasurable: 1

## By category (median ratio)

| category | cases | median ratio | reading |
|---|---|---|---|
| arith | 66 | 3.010 | behind |
| arrays | 20 | 4.715 | behind |
| builtin | 68 | 1.705 | behind |
| cond | 18 | 2.936 | behind |
| control | 19 | 2.792 | behind |
| data | 34 | 3.017 | behind |
| expand | 71 | 4.118 | behind |
| funcs | 12 | 1.652 | behind |
| glob | 12 | 2.534 | behind |
| jobs | 12 | 1.297 | behind |
| mixed | 8 | 2.010 | behind |
| parse | 8 | 14.725 | behind |
| redir | 18 | 1.310 | behind |
| startup | 10 | 3.151 | behind |
| strings | 18 | 5.420 | behind |
| subst | 14 | 0.538 | leading |

## Behind (worst first)

| case | category | rubash | gnu | ratio |
|---|---|---|---|---|
| arrays.assoc_get_miss | arrays | 255.91 us | 6.86 us | 37.304 |
| parse.n_control@2000 | parse | 242.43 ms | 7.89 ms | 30.731 |
| parse.n_funcs@1500 | parse | 216.29 ms | 7.79 ms | 27.763 |
| builtin.declare_local_like | builtin | 175.83 us | 7.62 us | 23.071 |
| arrays.append@100000 | arrays | 123.82 us | 6.37 us | 19.450 |
| parse.n_mixed@5000 | parse | 337.71 ms | 18.51 ms | 18.241 |
| arrays.assign_idx_mod | arrays | 73.33 us | 4.59 us | 15.981 |
| parse.n_simple@3000 | parse | 122.98 ms | 7.77 ms | 15.828 |
| parse.n_expand@2000 | parse | 225.40 ms | 16.55 ms | 13.622 |
| expand.arith_in_subscript | expand | 103.70 us | 7.78 us | 13.329 |
| builtin.declare_assign | builtin | 80.08 us | 6.21 us | 12.904 |
| expand.brace_nested | expand | 38.54 us | 3.31 us | 11.658 |
| arrays.sparse_set | arrays | 84.22 us | 7.99 us | 10.536 |
| builtin.typeset_assign | builtin | 93.26 us | 9.18 us | 10.155 |
| strings.build_50k | strings | 32.33 us | 3.21 us | 10.063 |
| arrays.length_elem | arrays | 46.49 us | 4.81 us | 9.672 |
| expand.param_indirect | expand | 56.85 us | 5.91 us | 9.620 |
| startup.biglib_source | startup | 239.95 ms | 25.06 ms | 9.573 |
| expand.history_char_bang | expand | 33.77 us | 3.55 us | 9.525 |
| arith.subscript_expr | arith | 67.04 us | 7.06 us | 9.489 |
| strings.case_conv_loop | strings | 56.37 us | 6.00 us | 9.391 |
| glob.star_all@300 | glob | 245.76 us | 26.18 us | 9.389 |
| strings.join_default | strings | 53.66 us | 5.89 us | 9.117 |
| expand.seconds_read | expand | 39.89 us | 4.55 us | 8.774 |
| arrays.append_loop | arrays | 56.95 us | 6.55 us | 8.696 |
| strings.trim_ws_param | strings | 50.07 us | 5.98 us | 8.374 |
| builtin.local_in_func | builtin | 94.61 us | 11.51 us | 8.220 |
| control.if_true | control | 42.00 us | 5.24 us | 8.015 |
| funcs.redefine | funcs | 38.28 us | 4.78 us | 8.013 |
| arrays.assoc_setget | arrays | 105.47 us | 13.17 us | 8.009 |
| redir.fd_open_close | redir | 108.52 us | 13.73 us | 7.903 |
| expand.multi_word_assign | expand | 35.18 us | 4.52 us | 7.778 |
| glob.extglob_plus | glob | 165.56 us | 22.19 us | 7.460 |
| strings.join_ifs_local | strings | 43.47 us | 5.96 us | 7.296 |
| arrays.iterate_keys@1000 | arrays | 115.29 us | 15.88 us | 7.262 |
| data.string_growth@50000 | data | 56.07 us | 7.76 us | 7.222 |
| strings.pattern_prefix | strings | 23.03 us | 3.21 us | 7.167 |
| data.read_ifs_fields@1000 | data | 114.56 us | 16.06 us | 7.135 |
| expand.lineno_read | expand | 33.84 us | 4.79 us | 7.068 |
| expand.brace_range_num | expand | 231.69 us | 33.48 us | 6.920 |
| builtin.declare_print | builtin | 193.72 us | 28.97 us | 6.687 |
| expand.brace_list | expand | 29.72 us | 4.61 us | 6.442 |
| expand.random_read | expand | 33.60 us | 5.28 us | 6.365 |
| expand.param_substr_s | expand | 39.52 us | 6.23 us | 6.346 |
| data.word_count_loop@1000 | data | 116.07 us | 18.29 us | 6.345 |
| parse.comment_dense | parse | 33.19 ms | 5.23 ms | 6.340 |
| expand.param_default_err_ok | expand | 33.41 us | 5.49 us | 6.083 |
| strings.repeat_printf | strings | 88.86 us | 14.62 us | 6.076 |
| expand.brace_range_alpha | expand | 101.14 us | 16.67 us | 6.068 |
| strings.compare_lt_loop | strings | 22.98 us | 3.90 us | 5.893 |
| arrays.read_elem | arrays | 39.78 us | 6.85 us | 5.804 |
| builtin.read_line | builtin | 129.93 us | 22.78 us | 5.703 |
| data.printf_bulk@10000 | data | 65.46 us | 11.55 us | 5.669 |
| strings.append_assign | strings | 33.36 us | 5.89 us | 5.666 |
| data.array_growth_read@100000 | data | 72.69 us | 13.03 us | 5.578 |
| mixed.dispatch_loop@5000 | mixed | 96.30 us | 17.27 us | 5.576 |
| expand.param_upper_all_s | expand | 39.95 us | 7.17 us | 5.572 |
| expand.brace_cartesian | expand | 58.70 us | 10.56 us | 5.558 |
| builtin.test_unary_z | builtin | 33.58 us | 6.16 us | 5.453 |
| expand.param_positional | expand | 24.25 us | 4.67 us | 5.191 |
| control.if_false_else | control | 39.43 us | 7.60 us | 5.186 |
| strings.pattern_glob_mid | strings | 23.02 us | 4.45 us | 5.175 |
| expand.param_suffix_rm_short_l | expand | 39.00 us | 7.69 us | 5.071 |
| expand.word_split | expand | 56.45 us | 11.13 us | 5.069 |
| expand.param_suffix_rm_long_s | expand | 33.47 us | 6.68 us | 5.011 |
| expand.param_substr_neg_s | expand | 38.81 us | 7.78 us | 4.991 |
| expand.param_replace_suffix_s | expand | 39.94 us | 8.04 us | 4.968 |
| data.kv_parse@50000 | data | 121.69 us | 24.93 us | 4.881 |
| expand.param_star_join | expand | 40.06 us | 8.21 us | 4.879 |
| expand.tilde_home | expand | 33.53 us | 6.89 us | 4.870 |
| arith.expand_eq | arith | 27.64 us | 5.71 us | 4.844 |
| arith.cmd_le | arith | 20.87 us | 4.31 us | 4.844 |
| cond.dbracket_v_unset | cond | 34.75 us | 7.17 us | 4.843 |
| expand.param_default_unset | expand | 37.97 us | 7.85 us | 4.836 |
| startup.true_c | startup | 18.19 ms | 3.77 ms | 4.825 |
| glob.extglob_neg | glob | 103.02 us | 21.36 us | 4.823 |
| arith.expand_preinc | arith | 34.80 us | 7.23 us | 4.812 |
| arith.cmd_predec | arith | 22.72 us | 4.74 us | 4.792 |
| expand.param_lower_first | expand | 38.15 us | 8.00 us | 4.769 |
| expand.param_nameref_read | expand | 26.75 us | 5.61 us | 4.769 |
| mixed.field_extract@20000 | mixed | 123.08 us | 25.85 us | 4.761 |
| arrays.read_negidx | arrays | 33.36 us | 7.06 us | 4.724 |
| strings.pad_printf | strings | 89.29 us | 18.97 us | 4.707 |
| arrays.iterate_atq@1000 | arrays | 82.68 us | 17.57 us | 4.705 |
| arith.cmd_preinc | arith | 22.24 us | 4.73 us | 4.704 |
| parse.long_line | parse | 17.26 ms | 3.68 ms | 4.686 |
| expand.glob_pattern_var | expand | 33.45 us | 7.16 us | 4.670 |
| startup.login_c | startup | 17.43 ms | 3.73 ms | 4.669 |
| expand.param_at_elem | expand | 29.70 us | 6.37 us | 4.665 |
| data.read_loop@100000 | data | 61.60 us | 13.21 us | 4.665 |
| funcs.call_local_arith | funcs | 105.19 us | 22.64 us | 4.647 |
| expand.double_nested_param | expand | 25.72 us | 5.54 us | 4.641 |
| arith.cmd_assign_add | arith | 20.83 us | 4.49 us | 4.640 |
| cond.dbracket_v_var | cond | 21.53 us | 4.67 us | 4.613 |
| jobs.kill_term | jobs | 17.81 ms | 3.88 ms | 4.586 |
| funcs.call_local | funcs | 64.20 us | 14.03 us | 4.577 |
| mixed.log_tally@20000 | mixed | 147.78 us | 32.51 us | 4.545 |
| control.elif_chain_hit3 | control | 91.33 us | 20.10 us | 4.544 |
| startup.interactive_c | startup | 17.28 ms | 3.81 ms | 4.535 |
| data.read_loop@1000 | data | 73.41 us | 16.27 us | 4.512 |
| expand.param_special_argc | expand | 24.94 us | 5.60 us | 4.457 |
| control.for_list | control | 421.93 us | 94.66 us | 4.457 |
| expand.brace_range_step | expand | 70.81 us | 16.00 us | 4.427 |
| cond.dbracket_pattern_var | cond | 24.11 us | 5.45 us | 4.420 |
| subst.procsub_read | subst | 3.68 ms | 835.26 us | 4.409 |
| arrays.compound_assign | arrays | 58.91 us | 13.42 us | 4.390 |
| expand.param_special_opts | expand | 23.53 us | 5.36 us | 4.388 |
| data.env_dump | data | 68.05 us | 15.64 us | 4.350 |
| arith.expand_assign_add | arith | 34.01 us | 7.89 us | 4.310 |
| expand.param_lower_all | expand | 36.92 us | 8.58 us | 4.304 |
| data.declare_p_assoc@10000 | data | 501.91 ms | 117.03 ms | 4.289 |
| expand.tilde_plus | expand | 23.51 us | 5.51 us | 4.267 |
| data.wc_style_count@100000 | data | 74.97 us | 17.96 us | 4.175 |
| expand.param_substr_l | expand | 32.93 us | 7.98 us | 4.128 |
| arith.big | arith | 23.20 us | 5.63 us | 4.123 |
| glob.bracket@200 | glob | 106.68 us | 25.90 us | 4.118 |
| expand.param_alt_set | expand | 36.58 us | 8.88 us | 4.118 |
| builtin.read_d_delim | builtin | 583.04 us | 142.33 us | 4.096 |
| expand.param_prefix_rm_long | expand | 44.18 us | 10.81 us | 4.087 |
| parse.quote_soup | parse | 16.98 us | 4.16 us | 4.080 |
| arrays.assoc_iterate@1000 | arrays | 64.47 us | 15.84 us | 4.070 |
| expand.param_default_set | expand | 36.51 us | 8.98 us | 4.067 |
| expand.param_keys | expand | 48.75 us | 11.99 us | 4.066 |
| expand.param_at_join | expand | 33.70 us | 8.29 us | 4.064 |
| arith.expand_predec | arith | 27.19 us | 6.69 us | 4.063 |
| cond.dbracket_str_eq | cond | 23.59 us | 5.81 us | 4.062 |
| arith.cmd_comma | arith | 21.19 us | 5.23 us | 4.054 |
| arrays.assoc_values@1000 | arrays | 64.44 us | 15.92 us | 4.047 |
| arrays.iterate_index@1000 | arrays | 64.30 us | 15.94 us | 4.033 |
| expand.param_assoc_keys | expand | 60.01 us | 14.91 us | 4.023 |
| data.read_ifs_fields@100000 | data | 78.02 us | 19.49 us | 4.002 |
| arith.expand_ne | arith | 22.44 us | 5.62 us | 3.995 |
| control.case_fallthrough | control | 88.66 us | 22.24 us | 3.986 |
| expand.param_braced | expand | 27.13 us | 6.85 us | 3.958 |
| arrays.assoc_fill@10000 | arrays | 26.49 us | 6.72 us | 3.942 |
| builtin.test_file_t | builtin | 27.41 us | 6.99 us | 3.919 |
| expand.param_replace_first_s | expand | 43.31 us | 11.06 us | 3.917 |
| builtin.continue_loop | builtin | 55.64 us | 14.36 us | 3.875 |
| data.assoc_fill@1000 | data | 64.25 us | 16.69 us | 3.850 |
| arith.expand_postinc | arith | 27.29 us | 7.19 us | 3.796 |
| arith.base2 | arith | 24.56 us | 6.50 us | 3.780 |
| data.set_dump | data | 69.81 us | 18.65 us | 3.743 |
| arith.expand_bnot | arith | 20.91 us | 5.62 us | 3.723 |
| builtin.bracket_expr | builtin | 27.31 us | 7.39 us | 3.695 |
| expand.param_substr_from_s | expand | 26.72 us | 7.28 us | 3.671 |
| expand.param_assoc_read | expand | 40.48 us | 11.12 us | 3.639 |
| arith.expand_gt | arith | 20.96 us | 5.76 us | 3.638 |
| expand.param_suffix_rm_long_l | expand | 48.48 us | 13.54 us | 3.580 |
| cond.dbracket_arith_cmp | cond | 27.37 us | 7.71 us | 3.550 |
| expand.param_replace_prefix_l | expand | 40.38 us | 11.47 us | 3.521 |
| arith.cmd_bnot | arith | 14.42 us | 4.13 us | 3.490 |
| arith.cmd_div | arith | 14.58 us | 4.18 us | 3.490 |
| arith.expand_land | arith | 20.61 us | 5.92 us | 3.480 |
| arith.cmd_postinc | arith | 14.50 us | 4.17 us | 3.479 |
| arith.cmd_land | arith | 14.57 us | 4.20 us | 3.469 |
| arith.expand_comma | arith | 26.94 us | 7.77 us | 3.466 |
| cond.dbracket_int_chain | cond | 24.73 us | 7.18 us | 3.444 |
| expand.param_upper_first_s | expand | 36.31 us | 10.58 us | 3.432 |
| arith.cmd_lor | arith | 14.52 us | 4.28 us | 3.395 |
| control.brace_group | control | 74.97 us | 22.10 us | 3.392 |
| cond.bracket_o_combo | cond | 38.20 us | 11.30 us | 3.381 |
| expand.param_suffix_rm_short_s | expand | 39.98 us | 11.83 us | 3.379 |
| control.while_count | control | 1.86 ms | 550.45 us | 3.372 |
| control.cond_dbracket_and | control | 44.62 us | 13.27 us | 3.362 |
| expand.param_length_arr | expand | 33.70 us | 10.03 us | 3.360 |
| arrays.assoc_get_hit | arrays | 26.97 us | 8.05 us | 3.348 |
| expand.param_alt_unset | expand | 26.60 us | 7.96 us | 3.343 |
| control.negation | control | 35.93 us | 10.89 us | 3.299 |
| cond.dbracket_file_s | cond | 36.59 us | 11.17 us | 3.276 |
| arrays.declare_p@1000 | arrays | 1.66 ms | 509.28 us | 3.269 |
| arith.cmd_gt | arith | 14.73 us | 4.55 us | 3.238 |
| data.array_fill_lines@1000 | data | 64.32 us | 19.89 us | 3.234 |
| arrays.copy_unset@1000 | arrays | 4.62 ms | 1.43 ms | 3.224 |
| arith.expand_lt | arith | 22.18 us | 6.89 us | 3.218 |
| builtin.test_str_eq | builtin | 25.75 us | 8.01 us | 3.214 |
| arith.cmd_assign_mod | arith | 15.63 us | 4.88 us | 3.199 |
| arith.let_chain | arith | 35.87 us | 11.21 us | 3.199 |
| data.grep_builtin_loop@100000 | data | 80.92 us | 25.33 us | 3.195 |
| startup.subshell_c | startup | 11.71 ms | 3.67 ms | 3.192 |
| arith.cmd_ne | arith | 14.44 us | 4.53 us | 3.189 |
| arith.expand_ternary | arith | 28.53 us | 8.96 us | 3.185 |
| arith.expand_mul | arith | 21.81 us | 6.88 us | 3.172 |
| expand.param_replace_suffix_l | expand | 54.26 us | 17.24 us | 3.148 |
| arith.cmd_neg | arith | 14.39 us | 4.57 us | 3.147 |
| builtin.test_int_lt | builtin | 24.98 us | 7.94 us | 3.146 |
| expand.param_substr_neg_l | expand | 37.00 us | 11.83 us | 3.127 |
| startup.empty_c | startup | 11.54 ms | 3.71 ms | 3.111 |
| builtin.printf_reuse | builtin | 83.63 us | 27.42 us | 3.050 |
| data.echo_bulk@10000 | data | 35.18 us | 11.55 us | 3.045 |
| builtin.printf_v_assign | builtin | 30.19 us | 9.94 us | 3.038 |
| arith.cmd_ternary | arith | 20.80 us | 6.85 us | 3.035 |
| arith.expand_lor | arith | 20.77 us | 6.87 us | 3.022 |
| expand.word_nosplit_quoted | expand | 16.88 us | 5.61 us | 3.009 |
| arith.expand_shr | arith | 20.79 us | 6.93 us | 2.998 |
| builtin.break_loop | builtin | 44.33 us | 14.79 us | 2.997 |
| data.word_count_loop@100000 | data | 48.83 us | 16.33 us | 2.990 |
| arith.expand_le | arith | 20.68 us | 6.93 us | 2.986 |
| builtin.shopt_query | builtin | 71.50 us | 23.95 us | 2.985 |
| expand.param_quoted_at_len | expand | 33.04 us | 11.09 us | 2.980 |
| cond.test_file_newer | cond | 32.59 us | 11.06 us | 2.948 |
| arith.cmd_eq | arith | 14.47 us | 4.91 us | 2.945 |
| data.array_fill_lines@100000 | data | 50.83 us | 17.26 us | 2.945 |
| expand.param_special_status | expand | 26.18 us | 8.91 us | 2.937 |
| arith.cmd_mul | arith | 16.29 us | 5.55 us | 2.935 |
| data.assoc_fill@100000 | data | 47.82 us | 16.33 us | 2.929 |
| arith.expand_assign_mul | arith | 21.72 us | 7.42 us | 2.926 |
| cond.bracket_combo | cond | 27.61 us | 9.44 us | 2.923 |
| arith.cmd_shr | arith | 14.31 us | 4.90 us | 2.921 |
| arith.cmd_lt | arith | 14.29 us | 4.94 us | 2.892 |
| arith.cmd_nested | arith | 20.94 us | 7.30 us | 2.870 |
| jobs.trap_set_clear | jobs | 58.86 us | 20.78 us | 2.833 |
| control.until_count | control | 1.20 ms | 430.68 us | 2.792 |
| glob.assign_array@200 | glob | 1.14 ms | 412.12 us | 2.777 |
| builtin.getopts_parse | builtin | 181.90 us | 66.43 us | 2.738 |
| glob.case_pattern | glob | 23.67 us | 8.65 us | 2.735 |
| redir.both_to_file | redir | 90.46 us | 33.18 us | 2.726 |
| strings.compare_eq_loop | strings | 12.92 us | 4.74 us | 2.724 |
| redir.devnull_write | redir | 44.87 us | 16.64 us | 2.696 |
| startup.assign_c | startup | 9.67 ms | 3.76 ms | 2.574 |
| expand.param_upper_first_l | expand | 29.59 us | 11.50 us | 2.573 |
| redir.file_append | redir | 83.50 us | 32.48 us | 2.571 |
| expand.param_substr_from_l | expand | 29.78 us | 11.72 us | 2.542 |
| redir.input_redirect_read | redir | 70.75 us | 28.01 us | 2.526 |
| data.read_mapfile@100000 | data | 1.66 us | 663 ns | 2.509 |
| data.declare_p_array@10000 | data | 290.05 ms | 116.60 ms | 2.488 |
| arrays.slice@1000 | arrays | 719.79 us | 289.42 us | 2.487 |
| expand.param_plain | expand | 16.93 us | 6.83 us | 2.480 |
| arith.cmd_bxor | arith | 14.50 us | 5.86 us | 2.474 |
| arith.expand_band | arith | 21.83 us | 9.01 us | 2.424 |
| startup.norc_c | startup | 8.88 ms | 3.71 ms | 2.397 |
| expand.param_length_str | expand | 33.75 us | 14.09 us | 2.396 |
| arith.expand_func_free_mix | arith | 25.00 us | 10.47 us | 2.387 |
| expand.param_upper_all_l | expand | 23.33 us | 9.96 us | 2.341 |
| glob.star_txt@200 | glob | 58.98 us | 25.29 us | 2.332 |
| arith.expand_bor | arith | 20.81 us | 8.96 us | 2.323 |
| builtin.compgen_word | builtin | 64.90 us | 29.02 us | 2.237 |
| builtin.echo_n_flag | builtin | 55.95 us | 25.32 us | 2.209 |
| arith.shift_chain | arith | 23.04 us | 10.46 us | 2.202 |
| cond.dbracket_str_ne | cond | 13.18 us | 6.02 us | 2.189 |
| builtin.unset_var | builtin | 20.55 us | 9.39 us | 2.188 |
| expand.param_default_assign | expand | 27.52 us | 12.73 us | 2.161 |
| strings.regex_simple | strings | 33.23 us | 15.39 us | 2.159 |
| arith.expand_mod | arith | 14.90 us | 6.91 us | 2.157 |
| expand.param_special_pid | expand | 16.71 us | 7.77 us | 2.152 |
| control.double_paren_cmd | control | 14.44 us | 6.74 us | 2.143 |
| arith.cmd_assign_mul | arith | 14.46 us | 6.75 us | 2.142 |
| control.case_first | control | 41.83 us | 19.63 us | 2.132 |
| arith.expand_neg | arith | 14.64 us | 6.87 us | 2.131 |
| builtin.complete_list | builtin | 36.60 us | 17.22 us | 2.125 |
| jobs.bg_pid_capture | jobs | 9.36 ms | 4.40 ms | 2.125 |
| builtin.let_simple | builtin | 17.74 us | 8.40 us | 2.112 |
| funcs.call_shift_args | funcs | 38.64 us | 18.30 us | 2.111 |
| arith.cmd_band | arith | 14.40 us | 6.89 us | 2.092 |
| jobs.trap_raise@200 | jobs | 83.58 us | 40.14 us | 2.082 |
| control.and_or | control | 121.99 us | 58.74 us | 2.077 |
| mixed.arg_parse@1000 | mixed | 8.47 us | 4.14 us | 2.044 |
| cond.dbracket_o_opt | cond | 22.88 us | 11.23 us | 2.038 |
| arith.expand_assign_mod | arith | 14.68 us | 7.25 us | 2.026 |
| builtin.echo_var | builtin | 49.72 us | 24.59 us | 2.022 |
| builtin.export_assign | builtin | 22.21 us | 10.99 us | 2.020 |
| control.test_bracket_chain | control | 74.01 us | 37.04 us | 1.998 |
| control.for_arith_inner | control | 1.07 ms | 537.52 us | 1.988 |
| builtin.builtin_run | builtin | 13.32 us | 6.74 us | 1.975 |
| mixed.token_machine@10000 | mixed | 155.22 us | 78.59 us | 1.975 |
| data.grep_builtin_loop@10 | data | 1.71 ms | 869.55 us | 1.970 |
| glob.starstar@300 | glob | 64.31 us | 32.68 us | 1.968 |
| builtin.eval_concat | builtin | 64.57 us | 32.89 us | 1.963 |
| glob.nomatch_nullglob | glob | 522.47 us | 266.40 us | 1.961 |
| subst.procsub_two | subst | 6.74 ms | 3.45 ms | 1.953 |
| jobs.disown_one | jobs | 16.62 ms | 8.56 ms | 1.941 |
| expand.param_prefix_rm_short | expand | 33.21 us | 17.23 us | 1.927 |
| arith.expand_nested | arith | 28.63 us | 14.95 us | 1.915 |
| startup.script_small | startup | 7.14 ms | 3.78 ms | 1.890 |
| builtin.read_fields | builtin | 61.75 us | 32.68 us | 1.889 |
| expand.param_replace_all_s | expand | 34.14 us | 18.13 us | 1.883 |
| data.grep_builtin_loop@1000 | data | 121.58 us | 64.90 us | 1.873 |
| funcs.call_nested3 | funcs | 71.80 us | 38.41 us | 1.869 |
| redir.stderr_merge | redir | 72.09 us | 38.58 us | 1.868 |
| mixed.name_transform@5000 | mixed | 198.78 us | 106.45 us | 1.867 |
| builtin.exec_redir_only | builtin | 57.59 us | 30.91 us | 1.863 |
| builtin.false_plain | builtin | 10.75 us | 5.79 us | 1.858 |
| arith.expand_shl | arith | 20.56 us | 11.10 us | 1.852 |
| expand.param_replace_prefix_s | expand | 43.45 us | 23.48 us | 1.851 |
| builtin.true_plain | builtin | 10.80 us | 5.88 us | 1.838 |
| cond.dbracket_or | cond | 21.15 us | 11.63 us | 1.819 |
| data.read_ifs_fields@10 | data | 778.00 us | 430.84 us | 1.806 |
| funcs.call_return_code | funcs | 44.16 us | 24.65 us | 1.791 |
| arith.cmd_bor | arith | 14.50 us | 8.22 us | 1.764 |
| builtin.kill_zero_self | builtin | 20.05 us | 11.38 us | 1.762 |
| builtin.command_run | builtin | 13.10 us | 7.51 us | 1.746 |
| builtin.readonly_set | builtin | 65.40 us | 37.83 us | 1.729 |
| strings.regex_nomatch | strings | 21.79 us | 12.72 us | 1.713 |
| builtin.alias_define | builtin | 32.67 us | 19.43 us | 1.681 |
| arith.cmd_sub | arith | 14.00 us | 8.55 us | 1.637 |
| expand.param_replace_first_l | expand | 37.23 us | 23.01 us | 1.618 |
| builtin.caller_in_func | builtin | 44.81 us | 27.89 us | 1.607 |
| cond.dbracket_file_e | cond | 21.86 us | 13.61 us | 1.606 |
| redir.clobber_guard | redir | 240.29 us | 149.98 us | 1.602 |
| redir.devfull_nowhere | redir | 74.67 us | 47.54 us | 1.571 |
| builtin.pwd_plain | builtin | 20.76 us | 13.33 us | 1.557 |
| cond.dbracket_file_d | cond | 22.98 us | 14.86 us | 1.546 |
| arith.expand_div | arith | 21.23 us | 13.76 us | 1.543 |
| arith.expand_add | arith | 22.51 us | 14.82 us | 1.519 |
| funcs.call_empty | funcs | 52.63 us | 34.80 us | 1.512 |
| expand.tilde_user | expand | 49.70 us | 33.46 us | 1.485 |
| strings.regex_groups | strings | 55.94 us | 38.12 us | 1.468 |
| arith.for_header | arith | 84.26 us | 57.52 us | 1.465 |
| data.read_mapfile@1000 | data | 8.18 us | 5.59 us | 1.463 |
| arith.expand_bxor | arith | 21.25 us | 14.58 us | 1.458 |
| builtin.return_in_func | builtin | 37.16 us | 25.66 us | 1.448 |
| arith.cmd_mod | arith | 14.53 us | 10.31 us | 1.410 |
| redir.file_truncate_write | redir | 164.57 us | 116.80 us | 1.409 |
| control.case_last | control | 32.82 us | 23.31 us | 1.408 |
| funcs.declare_f_dump | funcs | 38.66 us | 27.46 us | 1.408 |
| cond.dbracket_file_f | cond | 17.84 us | 12.68 us | 1.406 |
| arith.cmd_func_free_mix | arith | 14.72 us | 10.47 us | 1.406 |
| expand.param_replace_all_l | expand | 37.04 us | 26.91 us | 1.376 |
| glob.nomatch_plain | glob | 397.40 us | 295.35 us | 1.346 |
| funcs.export_f | funcs | 5.85 ms | 4.37 ms | 1.339 |
| jobs.trap_debug_stmt | jobs | 121.55 us | 91.12 us | 1.334 |
| arith.cmd_shl | arith | 11.09 us | 8.44 us | 1.315 |
| builtin.printf_fmt_nums | builtin | 75.68 us | 57.91 us | 1.307 |
| data.array_fill_lines@10 | data | 784.92 us | 606.21 us | 1.295 |
| data.word_count_loop@10 | data | 883.63 us | 690.90 us | 1.279 |
| builtin.mapfile_small | builtin | 1.40 ms | 1.10 ms | 1.276 |
| jobs.bg_wait_one | jobs | 83.42 ms | 66.15 ms | 1.261 |
| builtin.bgfg_job_cycle | builtin | 6.69 ms | 5.31 ms | 1.260 |
| subst.subshell_pipe | subst | 3.74 ms | 2.98 ms | 1.255 |
| glob.dotfiles | glob | 186.42 us | 149.26 us | 1.249 |
| arith.expand_pow | arith | 20.63 us | 16.71 us | 1.235 |
| builtin.let_multi | builtin | 27.99 us | 22.84 us | 1.226 |
| redir.fd_dup_write | redir | 21.64 us | 17.86 us | 1.212 |
| builtin.fc_list | builtin | 28.19 us | 23.36 us | 1.207 |
| jobs.kill_check_loop | jobs | 267.02 ms | 228.43 ms | 1.169 |
| strings.concat_subst | strings | 90.42 us | 77.52 us | 1.166 |
| builtin.eval_simple | builtin | 33.43 us | 29.08 us | 1.150 |
| jobs.jobs_list_live | jobs | 184.42 ms | 165.99 ms | 1.111 |
| startup.script_noop | startup | 4.19 ms | 3.78 ms | 1.108 |

## Close

| case | category | rubash | gnu | ratio |
|---|---|---|---|---|
| jobs.sigpipe_shape | jobs | 10.44 ms | 9.50 ms | 1.098 |
| data.read_loop@10 | data | 850.86 us | 780.38 us | 1.090 |
| builtin.times_plain | builtin | 21.80 us | 20.18 us | 1.081 |
| builtin.echo_plain | builtin | 32.05 us | 29.81 us | 1.075 |
| strings.regex_alt | strings | 29.71 us | 28.00 us | 1.061 |
| builtin.shift_one | builtin | 19.53 us | 18.52 us | 1.054 |
| builtin.type_builtin | builtin | 23.72 us | 22.88 us | 1.037 |
| arith.expand_sub | arith | 21.48 us | 20.73 us | 1.036 |
| mixed.report_table@2000 | mixed | 60.30 us | 59.17 us | 1.019 |
| builtin.readarray_small | builtin | 1.17 ms | 1.16 ms | 1.002 |
| funcs.call_args | funcs | 33.36 us | 33.31 us | 1.001 |
| jobs.bg_many@20 | jobs | 5.83 ms | 5.84 ms | 0.997 |
| builtin.printf_fmt_s | builtin | 55.45 us | 55.73 us | 0.995 |
| redir.herestring_read | redir | 41.59 us | 41.81 us | 0.995 |
| mixed.config_parse@2000 | mixed | 133.64 us | 134.37 us | 0.995 |
| arith.cmd_pow | arith | 14.43 us | 14.62 us | 0.987 |
| arith.cmd_add | arith | 14.63 us | 14.88 us | 0.983 |

## Leading (best first)

| case | category | rubash | gnu | ratio |
|---|---|---|---|---|
| subst.cmd_builtin_echo | subst | 55.84 us | 1.73 ms | 0.032 |
| control.pipeline_status | control | 116.93 us | 3.25 ms | 0.036 |
| redir.herestring_cat | redir | 147.94 us | 3.78 ms | 0.039 |
| builtin.pwd_subst | builtin | 36.31 us | 922.83 us | 0.039 |
| redir.pipe_two_ext | redir | 112.79 us | 2.85 ms | 0.040 |
| subst.backquote_echo | subst | 37.39 us | 940.45 us | 0.040 |
| redir.pipe_three_ext | redir | 247.39 us | 5.02 ms | 0.049 |
| builtin.colon_plain | builtin | 567 ns | 10.84 us | 0.052 |
| redir.heredoc_expand | redir | 233.56 us | 4.16 ms | 0.056 |
| subst.arith_nested_subst | subst | 96.02 us | 1.25 ms | 0.077 |
| redir.heredoc_small | redir | 231.80 us | 2.60 ms | 0.089 |
| subst.cmd_true | subst | 120.22 us | 1.14 ms | 0.106 |
| subst.cmd_nested2 | subst | 332.26 us | 3.09 ms | 0.107 |
| funcs.call_in_subst | funcs | 234.04 us | 2.08 ms | 0.113 |
| expand.default_cmdsubst | expand | 115.71 us | 534.44 us | 0.217 |
| subst.subshell_assign | subst | 331.45 us | 1.46 ms | 0.227 |
| builtin.kill_l_list | builtin | 26.50 us | 116.71 us | 0.227 |
| glob.question@200 | glob | 41.06 us | 164.71 us | 0.249 |
| builtin.enable_list | builtin | 27.01 us | 101.49 us | 0.266 |
| builtin.wait_none | builtin | 11.15 us | 40.38 us | 0.276 |
| funcs.recursive_fib15 | funcs | 1177.62 ms | 4042.36 ms | 0.291 |
| redir.pipe_two_builtin | redir | 556.63 us | 1.62 ms | 0.344 |
| builtin.read_array | builtin | 19.14 us | 48.57 us | 0.394 |
| data.assoc_fill@10 | data | 772.51 us | 1.96 ms | 0.395 |
| builtin.umask_read | builtin | 24.39 us | 60.15 us | 0.405 |
| builtin.cd_dot | builtin | 19.17 us | 45.90 us | 0.418 |
| builtin.command_v | builtin | 23.68 us | 55.61 us | 0.426 |
| data.sort_via_array@10 | data | 477.57 us | 1.04 ms | 0.458 |
| builtin.ulimit_read | builtin | 27.49 us | 59.62 us | 0.461 |
| builtin.history_list | builtin | 34.07 us | 71.36 us | 0.477 |
| data.sort_via_array@1000 | data | 8.19 us | 17.01 us | 0.482 |
| subst.cmd_big_output | subst | 3.36 ms | 6.69 ms | 0.502 |
| cond.dbracket_regex_var | cond | 38.36 us | 72.94 us | 0.526 |
| cond.dbracket_not | cond | 17.68 us | 32.69 us | 0.541 |
| expand.nested_cmdsubst | expand | 1.03 ms | 1.87 ms | 0.553 |
| subst.cmd_self | subst | 6.18 ms | 10.78 ms | 0.573 |
| builtin.set_query | builtin | 38.80 us | 64.95 us | 0.597 |
| builtin.hash_lookup | builtin | 47.52 us | 78.55 us | 0.605 |
| builtin.dirs_list | builtin | 22.85 us | 37.51 us | 0.609 |
| builtin.jobs_list | builtin | 24.04 us | 38.61 us | 0.623 |
| strings.join_ifs | strings | 389.86 us | 612.75 us | 0.636 |
| builtin.echo_e_escapes | builtin | 47.54 us | 71.74 us | 0.663 |
| builtin.popd_pair | builtin | 55.23 us | 82.78 us | 0.667 |
| builtin.help_one | builtin | 33.33 us | 47.39 us | 0.703 |
| subst.cmd_assign_trim | subst | 553.28 us | 742.43 us | 0.745 |
| control.select_pick | control | 933.39 us | 1.16 ms | 0.805 |
| subst.cmd_ext_date | subst | 2.70 ms | 3.21 ms | 0.842 |
| data.sort_via_array@100000 | data | 2.73 us | 3.22 us | 0.846 |
| subst.procsub_cat | subst | 3.16 ms | 3.58 ms | 0.881 |
| control.subshell_group | control | 537.28 us | 605.16 us | 0.888 |
| jobs.trap_exit | jobs | 7.99 ms | 8.53 ms | 0.938 |
| redir.pipe_data_10k | redir | 1.61 us | 1.71 us | 0.941 |
| data.read_mapfile@10 | data | 378.84 us | 399.53 us | 0.948 |

## Unmeasurable

- arith.octal_hex (rubash: verify-failed / gnu: ok)
