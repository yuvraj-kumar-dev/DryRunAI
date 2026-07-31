#!/usr/bin/env python3
"""
Generates a 50-problem DSA question bank (Array / String / Linked List,
Easy / Medium / Hard) as structured JSON for an AI DSA interview platform.

IMPORTANT — sourcing note:
All problem_statement / constraints / examples / hints text below is
written from scratch. Only the well-known problem *names* (e.g. "Two Sum",
"Reverse Linked List") and the underlying algorithmic task are referenced
from public curricula (LeetCode, Striver's A2Z Sheet, NeetCode 150, Blind 75)
-- no statement text is copied from any of those platforms. `source_reference`
and `prep_sheets` are pointers for attribution / further practice, not
embedded copyrighted text.
"""

import json
from datetime import date
from pathlib import Path

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "app" / "data" / "dsa_problems_v0.json"

PROBLEMS = []

def add(id, title, topic, difficulty, patterns, statement, constraints,
        examples, hints, complexity, follow_up, source_name, prep_sheets):
    PROBLEMS.append({
        "id": id,
        "title": title,
        "topic": topic,
        "difficulty": difficulty,
        "patterns": patterns,
        "problem_statement": statement,
        "constraints": constraints,
        "examples": examples,
        "hints": hints,
        "optimal_complexity": complexity,
        "follow_up_questions": follow_up,
        "source_reference": {"platform": source_name[0], "problem_name": source_name[1]},
        "prep_sheets_seen_on": prep_sheets,
    })

# =========================================================================
# ARRAY -- EASY
# =========================================================================

add("arr-e-01", "Two Sum", "Array", "Easy",
    ["hash-map", "one-pass"],
    "Given an array of integers and a target value, return the indices of "
    "the two numbers that add up to the target. Assume exactly one valid "
    "pair exists, and the same element cannot be used twice.",
    ["2 <= n <= 10^4", "Array may contain negative numbers and duplicates",
     "Exactly one valid answer exists"],
    [{"input": "nums = [2,7,11,15], target = 9", "output": "[0,1]",
      "explanation": "nums[0] + nums[1] = 2 + 7 = 9"},
     {"input": "nums = [3,2,4], target = 6", "output": "[1,2]",
      "explanation": "nums[1] + nums[2] = 2 + 4 = 6"}],
    ["Brute force checks every pair in O(n^2) -- can you avoid the nested loop?",
     "As you scan, store each value's index in a hash map so you can check for its complement in O(1)."],
    {"time": "O(n)", "space": "O(n)"},
    ["What if the array is sorted -- can you do it with O(1) extra space?",
     "How would you handle multiple valid pairs and return all of them?"],
    ("LeetCode", "Two Sum"),
    ["Striver A2Z", "NeetCode 150", "Blind 75"])

add("arr-e-02", "Best Time to Buy and Sell Stock", "Array", "Easy",
    ["greedy", "one-pass"],
    "Given an array where each element is a stock's price on a given day, "
    "find the maximum profit from a single buy followed by a single sell "
    "(buy must occur before sell). Return 0 if no profit is possible.",
    ["1 <= n <= 10^5", "0 <= price <= 10^4"],
    [{"input": "prices = [7,1,5,3,6,4]", "output": "5",
      "explanation": "Buy at 1, sell at 6, profit = 5"},
     {"input": "prices = [7,6,4,3,1]", "output": "0",
      "explanation": "Prices only fall, so no profit is possible"}],
    ["Track the minimum price seen so far as you scan left to right.",
     "At each day, the best possible profit if sold today is price[i] - min_so_far."],
    {"time": "O(n)", "space": "O(1)"},
    ["How does this change if you're allowed multiple transactions?",
     "What if a cooldown period is required after selling?"],
    ("LeetCode", "Best Time to Buy and Sell Stock"),
    ["Striver A2Z", "NeetCode 150", "Blind 75"])

add("arr-e-03", "Contains Duplicate", "Array", "Easy",
    ["hash-set"],
    "Given an integer array, determine whether any value appears at least twice.",
    ["1 <= n <= 10^5"],
    [{"input": "[1,2,3,1]", "output": "true", "explanation": "1 appears twice"},
     {"input": "[1,2,3,4]", "output": "false", "explanation": "all values are unique"}],
    ["Sorting lets you check adjacent elements, but costs O(n log n).",
     "A hash set gives O(n) time at the cost of O(n) space."],
    {"time": "O(n)", "space": "O(n)"},
    ["How would you solve this with O(1) extra space if the input is sorted?",
     "How would you find duplicates within a sliding window of size k?"],
    ("LeetCode", "Contains Duplicate"),
    ["NeetCode 150", "Blind 75"])

add("arr-e-04", "Move Zeroes", "Array", "Easy",
    ["two-pointer", "in-place"],
    "Given an integer array, move all zeroes to the end while maintaining "
    "the relative order of the non-zero elements, in-place, without "
    "allocating a copy of the array.",
    ["1 <= n <= 10^4"],
    [{"input": "[0,1,0,3,12]", "output": "[1,3,12,0,0]"},
     {"input": "[0,0,1]", "output": "[1,0,0]"}],
    ["Use a slow pointer marking where the next non-zero element should go.",
     "Swap instead of overwrite so you don't need a second pass to fill zeroes."],
    {"time": "O(n)", "space": "O(1)"},
    ["Can you minimize the total number of writes/swaps?",
     "What if you needed to move all zeroes to the front instead?"],
    ("LeetCode", "Move Zeroes"),
    ["Striver A2Z", "NeetCode 150"])

add("arr-e-05", "Majority Element", "Array", "Easy",
    ["boyer-moore-voting"],
    "Given an array of size n, find the element that appears more than "
    "n/2 times. You may assume such an element always exists.",
    ["1 <= n <= 5*10^4"],
    [{"input": "[3,2,3]", "output": "3"},
     {"input": "[2,2,1,1,1,2,2]", "output": "2"}],
    ["A hash map of counts works but uses O(n) space -- can you do O(1) space?",
     "Boyer-Moore voting: maintain a candidate and a counter; the majority element survives the cancellations."],
    {"time": "O(n)", "space": "O(1)"},
    ["How would you solve it if no guaranteed majority exists (find elements appearing > n/3 times)?",
     "How would you adapt this for a streaming input where you can't revisit earlier elements?"],
    ("LeetCode", "Majority Element"),
    ["Striver A2Z", "NeetCode 150"])

# =========================================================================
# ARRAY -- MEDIUM
# =========================================================================

add("arr-m-01", "Maximum Subarray (Kadane's Algorithm)", "Array", "Medium",
    ["dynamic-programming", "kadane"],
    "Given an integer array that may include negative numbers, find the "
    "contiguous subarray with the largest sum and return that sum.",
    ["1 <= n <= 10^5", "-10^4 <= nums[i] <= 10^4"],
    [{"input": "[-2,1,-3,4,-1,2,1,-5,4]", "output": "6",
      "explanation": "The subarray [4,-1,2,1] sums to 6"},
     {"input": "[1]", "output": "1"}],
    ["At each index, decide whether to extend the previous subarray or start fresh here.",
     "Track a running sum and a global maximum as you go."],
    {"time": "O(n)", "space": "O(1)"},
    ["How would you also return the actual subarray, not just the sum?",
     "How would you extend this to a 2D matrix (maximum-sum submatrix)?"],
    ("LeetCode", "Maximum Subarray"),
    ["Striver A2Z", "NeetCode 150", "Blind 75"])

add("arr-m-02", "Product of Array Except Self", "Array", "Medium",
    ["prefix-suffix-product"],
    "Given an integer array, return an array where each element is the "
    "product of all other elements except itself, without using division "
    "and in O(n) time.",
    ["2 <= n <= 10^5", "product of any prefix/suffix fits a 32-bit integer"],
    [{"input": "[1,2,3,4]", "output": "[24,12,8,6]"},
     {"input": "[-1,1,0,-3,3]", "output": "[0,0,9,0,0]"}],
    ["Compute prefix products in one pass and suffix products in another, then multiply.",
     "For O(1) extra space (excluding output), fold the suffix pass directly into the output array."],
    {"time": "O(n)", "space": "O(1) extra excluding output"},
    ["How does the approach change if division were allowed but zeroes could appear?",
     "How would you handle this as a streaming problem where the array grows?"],
    ("LeetCode", "Product of Array Except Self"),
    ["Striver A2Z", "NeetCode 150", "Blind 75"])

add("arr-m-03", "3Sum", "Array", "Medium",
    ["two-pointer", "sorting"],
    "Given an integer array, find all unique triplets that sum to zero. "
    "The solution set must not contain duplicate triplets.",
    ["3 <= n <= 3000"],
    [{"input": "[-1,0,1,2,-1,-4]", "output": "[[-1,-1,2],[-1,0,1]]"},
     {"input": "[0,1,1]", "output": "[]"}],
    ["Sort the array first -- this makes duplicate-skipping and two-pointer scanning straightforward.",
     "Fix one element, then use two pointers on the remaining sorted subarray to find pairs summing to its negation."],
    {"time": "O(n^2)", "space": "O(1) extra excluding output"},
    ["How would you extend this to 4Sum or general k-Sum?",
     "How would you count triplets close to a target rather than exactly equal to it?"],
    ("LeetCode", "3Sum"),
    ["Striver A2Z", "NeetCode 150", "Blind 75"])

add("arr-m-04", "Sort Colors (Dutch National Flag)", "Array", "Medium",
    ["three-pointer", "in-place-partition"],
    "Given an array containing only the values 0, 1, and 2, sort it "
    "in-place in a single pass without using a library sort.",
    ["1 <= n <= 300"],
    [{"input": "[2,0,2,1,1,0]", "output": "[0,0,1,1,2,2]"},
     {"input": "[2,0,1]", "output": "[0,1,2]"}],
    ["Maintain three pointers -- low, mid, and high -- partitioning the array as you scan.",
     "When you swap the high pointer's element in, don't advance mid yet -- the swapped-in value still needs checking."],
    {"time": "O(n)", "space": "O(1)"},
    ["How would this generalize to k distinct values instead of just 3?",
     "How is this related to the quicksort partitioning scheme?"],
    ("LeetCode", "Sort Colors"),
    ["Striver A2Z", "NeetCode 150"])

add("arr-m-05", "Next Permutation", "Array", "Medium",
    ["array-manipulation"],
    "Given an array of integers representing a permutation, rearrange it "
    "in-place into the next lexicographically greater permutation. If none "
    "exists, rearrange it into the lowest possible order (sorted ascending).",
    ["1 <= n <= 100"],
    [{"input": "[1,2,3]", "output": "[1,3,2]"},
     {"input": "[3,2,1]", "output": "[1,2,3]"}],
    ["Scan from the right to find the first index where the sequence stops decreasing.",
     "Swap that element with the smallest element to its right that's still larger than it, then reverse the suffix."],
    {"time": "O(n)", "space": "O(1)"},
    ["How would you find the previous permutation instead?",
     "How would you find the k-th permutation directly without generating all of them?"],
    ("LeetCode", "Next Permutation"),
    ["Striver A2Z"])

add("arr-m-06", "Rotate Array", "Array", "Medium",
    ["array-reversal", "in-place"],
    "Given an array, rotate it to the right by k steps, in-place, using "
    "O(1) extra space.",
    ["1 <= n <= 10^5", "0 <= k <= 10^5"],
    [{"input": "nums=[1,2,3,4,5,6,7], k=3", "output": "[5,6,7,1,2,3,4]"},
     {"input": "nums=[-1,-100,3,99], k=2", "output": "[3,99,-1,-100]"}],
    ["Reduce k modulo n first, since rotating by n is a no-op.",
     "Three reversals -- the whole array, then each of the two segments -- rotate it in-place in O(n)."],
    {"time": "O(n)", "space": "O(1)"},
    ["How would you rotate left instead of right?",
     "How does the reversal trick generalize to rotating a singly linked list?"],
    ("LeetCode", "Rotate Array"),
    ["Striver A2Z", "NeetCode 150"])

add("arr-m-07", "Subarray Sum Equals K", "Array", "Medium",
    ["prefix-sum", "hash-map"],
    "Given an integer array and an integer k, return the total number of "
    "contiguous subarrays whose sum equals k.",
    ["1 <= n <= 2*10^4", "array can contain negative numbers"],
    [{"input": "nums=[1,1,1], k=2", "output": "2"},
     {"input": "nums=[1,2,3], k=3", "output": "2"}],
    ["Maintain a running prefix sum and a hash map counting how many times each prefix sum has occurred.",
     "At each index, the number of valid subarrays ending here equals how many times (prefix_sum - k) has been seen before."],
    {"time": "O(n)", "space": "O(n)"},
    ["If the array only contained non-negative numbers, would a sliding window work instead?",
     "How would you find the longest subarray summing to k instead of counting them?"],
    ("LeetCode", "Subarray Sum Equals K"),
    ["Striver A2Z", "NeetCode 150"])

add("arr-m-08", "Merge Intervals", "Array", "Medium",
    ["sorting", "interval-merging"],
    "Given a collection of intervals, merge all overlapping intervals and "
    "return the resulting non-overlapping set.",
    ["1 <= n <= 10^4", "intervals given as [start, end] with start <= end"],
    [{"input": "[[1,3],[2,6],[8,10],[15,18]]", "output": "[[1,6],[8,10],[15,18]]"},
     {"input": "[[1,4],[4,5]]", "output": "[[1,5]]"}],
    ["Sort the intervals by start time first -- this makes overlaps trivial to detect in one pass.",
     "Two intervals overlap when the next interval's start is <= the current merged interval's end."],
    {"time": "O(n log n)", "space": "O(n)"},
    ["How would you insert a new interval into an already-sorted, non-overlapping list efficiently?",
     "How would you find the minimum number of intervals to remove to make the rest non-overlapping?"],
    ("LeetCode", "Merge Intervals"),
    ["Striver A2Z", "NeetCode 150", "Blind 75"])

add("arr-m-09", "Set Matrix Zeroes", "Array", "Medium",
    ["in-place-matrix-manipulation"],
    "Given an m x n matrix, if an element is 0, set its entire row and "
    "column to 0. Do this in-place using O(1) extra space.",
    ["1 <= m, n <= 200"],
    [{"input": "[[1,1,1],[1,0,1],[1,1,1]]", "output": "[[1,0,1],[0,0,0],[1,0,1]]"},
     {"input": "[[0,1,2,0],[3,4,5,2],[1,3,1,5]]",
      "output": "[[0,0,0,0],[0,4,5,0],[0,3,1,0]]"}],
    ["A naive approach marks zero positions in a separate set -- this uses O(m+n) space; can you do better?",
     "Use the first row and first column of the matrix itself as markers, handling the top-left cell's dual role carefully."],
    {"time": "O(mn)", "space": "O(1)"},
    ["Why does the first-row/first-column marker trick need an extra flag for the top-left cell?",
     "How would this change for a sparse matrix representation?"],
    ("LeetCode", "Set Matrix Zeroes"),
    ["Striver A2Z", "NeetCode 150"])

# =========================================================================
# ARRAY -- HARD
# =========================================================================

add("arr-h-01", "Trapping Rain Water", "Array", "Hard",
    ["two-pointer", "prefix-max"],
    "Given an array representing an elevation map where each bar has "
    "width 1, compute how much rainwater it can trap after raining.",
    ["1 <= n <= 2*10^4", "0 <= height[i] <= 10^5"],
    [{"input": "[0,1,0,2,1,0,1,3,2,1,2,1]", "output": "6"},
     {"input": "[4,2,0,3,2,5]", "output": "9"}],
    ["Water trapped at index i is bounded by min(max height to its left, max height to its right) minus height[i].",
     "Two pointers from both ends, tracking a running left-max and right-max, avoid needing precomputed arrays."],
    {"time": "O(n)", "space": "O(1)"},
    ["How would you solve the 2D version (Trapping Rain Water II) with a heap?",
     "How does the two-pointer approach avoid needing the full left-max/right-max arrays?"],
    ("LeetCode", "Trapping Rain Water"),
    ["Striver A2Z", "NeetCode 150", "Blind 75"])

add("arr-h-02", "First Missing Positive", "Array", "Hard",
    ["in-place-hashing", "cyclic-sort"],
    "Given an unsorted integer array, find the smallest missing positive "
    "integer, using O(n) time and O(1) extra space.",
    ["1 <= n <= 5*10^5"],
    [{"input": "[1,2,0]", "output": "3"},
     {"input": "[3,4,-1,1]", "output": "2"},
     {"input": "[7,8,9,11,12]", "output": "1"}],
    ["The answer must lie between 1 and n+1, so values outside that range never matter.",
     "Use the array itself as a hash table: place each value v at index v-1 by swapping, then scan for the first index that doesn't hold its expected value."],
    {"time": "O(n)", "space": "O(1)"},
    ["How would this change if the array could contain duplicates of very large magnitude?",
     "Can you find the k-th missing positive with a similar technique?"],
    ("LeetCode", "First Missing Positive"),
    ["Striver A2Z", "NeetCode 150", "Blind 75"])

add("arr-h-03", "Median of Two Sorted Arrays", "Array", "Hard",
    ["binary-search", "partitioning"],
    "Given two sorted arrays of possibly different sizes, find the median "
    "of the combined array in O(log(min(m,n))) time.",
    ["0 <= m, n <= 1000", "at least one array is non-empty"],
    [{"input": "nums1=[1,3], nums2=[2]", "output": "2.0"},
     {"input": "nums1=[1,2], nums2=[3,4]", "output": "2.5"}],
    ["Merging both arrays and taking the middle works but is O(m+n) -- think about binary searching for the correct partition point instead.",
     "Binary search on the smaller array for a partition such that every element on the left side is <= every element on the right side across both arrays."],
    {"time": "O(log(min(m,n)))", "space": "O(1)"},
    ["How would you generalize this to finding the median of k sorted arrays?",
     "What breaks if you binary search on the larger array instead of the smaller one?"],
    ("LeetCode", "Median of Two Sorted Arrays"),
    ["Striver A2Z", "NeetCode 150", "Blind 75"])

add("arr-h-04", "Sliding Window Maximum", "Array", "Hard",
    ["monotonic-deque"],
    "Given an array and a window size k, return the maximum value in "
    "each sliding window as it moves from the left of the array to the right.",
    ["1 <= n <= 10^5", "1 <= k <= n"],
    [{"input": "nums=[1,3,-1,-3,5,3,6,7], k=3", "output": "[3,3,5,5,6,7]"},
     {"input": "nums=[1], k=1", "output": "[1]"}],
    ["A brute-force scan of every window is O(nk) -- can a data structure maintain the max incrementally?",
     "Use a monotonic decreasing deque of indices: pop smaller elements from the back before pushing, and pop from the front once indices fall outside the window."],
    {"time": "O(n)", "space": "O(k)"},
    ["How would you adapt this to track the sliding window minimum instead?",
     "How would you support this over a live stream where k can change dynamically?"],
    ("LeetCode", "Sliding Window Maximum"),
    ["Striver A2Z", "NeetCode 150"])

# =========================================================================
# STRING -- EASY
# =========================================================================

add("str-e-01", "Valid Anagram", "String", "Easy",
    ["hash-map", "frequency-count"],
    "Given two strings, determine whether the second is an anagram of the "
    "first (uses exactly the same characters with the same frequency, "
    "possibly reordered).",
    ["1 <= length <= 5*10^4", "lowercase English letters"],
    [{"input": "s='anagram', t='nagaram'", "output": "true"},
     {"input": "s='rat', t='car'", "output": "false"}],
    ["Sorting both strings and comparing works but costs O(n log n) -- a frequency count is O(n).",
     "A single array of 26 counters is enough; increment for s and decrement for t, then check all zeros."],
    {"time": "O(n)", "space": "O(1) for a fixed alphabet"},
    ["How would you handle Unicode characters instead of just lowercase English letters?",
     "How would you check if one string is an anagram of any substring of another?"],
    ("LeetCode", "Valid Anagram"),
    ["Striver A2Z", "NeetCode 150"])

add("str-e-02", "Valid Palindrome", "String", "Easy",
    ["two-pointer"],
    "Given a string, determine if it's a palindrome after converting all "
    "uppercase letters to lowercase and removing all non-alphanumeric characters.",
    ["1 <= length <= 2*10^5"],
    [{"input": "'A man, a plan, a canal: Panama'", "output": "true"},
     {"input": "'race a car'", "output": "false"}],
    ["Two pointers starting from both ends can skip non-alphanumeric characters as they move inward.",
     "Compare characters case-insensitively without building a separate cleaned string, to save space."],
    {"time": "O(n)", "space": "O(1)"},
    ["How would you solve it if you're allowed to delete at most one character (Valid Palindrome II)?",
     "How would you find the longest palindromic substring instead of validating the whole string?"],
    ("LeetCode", "Valid Palindrome"),
    ["NeetCode 150", "Striver A2Z"])

add("str-e-03", "Reverse String", "String", "Easy",
    ["two-pointer", "in-place"],
    "Given an array of characters representing a string, reverse it "
    "in-place using O(1) extra space.",
    ["1 <= length <= 10^5"],
    [{"input": "['h','e','l','l','o']", "output": "['o','l','l','e','h']"},
     {"input": "['H','a','n','n','a','h']", "output": "['h','a','n','n','a','H']"}],
    ["Two pointers at opposite ends, swapping and moving inward, do this in a single pass.",
     "No auxiliary array is needed since the swap can happen directly in the given array."],
    {"time": "O(n)", "space": "O(1)"},
    ["How would you reverse only the vowels in a string, keeping other characters fixed?",
     "How would you reverse words in a sentence while keeping each word's letters in order?"],
    ("LeetCode", "Reverse String"),
    ["NeetCode 150"])

add("str-e-04", "Find the Index of the First Occurrence in a String", "String", "Easy",
    ["string-matching"],
    "Given a haystack string and a needle string, return the index of the "
    "first occurrence of needle in haystack, or -1 if needle does not occur.",
    ["0 <= haystack.length, needle.length <= 5*10^4"],
    [{"input": "haystack='sadbutsad', needle='sad'", "output": "0"},
     {"input": "haystack='leetcode', needle='leeto'", "output": "-1"}],
    ["A brute-force check at every starting position is O(nm) -- acceptable for small inputs, but think about a faster approach.",
     "KMP or Rabin-Karp reduce this to O(n+m) by avoiding redundant re-comparisons."],
    {"time": "O(n+m) with KMP", "space": "O(m)"},
    ["Can you explain how the KMP failure function avoids re-scanning characters?",
     "How would Rabin-Karp's rolling hash approach compare in the presence of hash collisions?"],
    ("LeetCode", "Find the Index of the First Occurrence in a String"),
    ["Striver A2Z"])

add("str-e-05", "Longest Common Prefix", "String", "Easy",
    ["string-comparison"],
    "Given an array of strings, find the longest common prefix shared by "
    "all of them. Return an empty string if there is no common prefix.",
    ["1 <= n <= 200"],
    [{"input": "['flower','flow','flight']", "output": "'fl'"},
     {"input": "['dog','racecar','car']", "output": "''"}],
    ["Compare characters column by column across all strings, stopping at the first mismatch.",
     "Alternatively, sort the array -- the common prefix of the whole array equals the common prefix of just the first and last strings after sorting."],
    {"time": "O(S) total characters", "space": "O(1)"},
    ["How would you find the longest common suffix instead?",
     "How would this scale if the strings were stored across a distributed system?"],
    ("LeetCode", "Longest Common Prefix"),
    ["Striver A2Z", "NeetCode 150"])

# =========================================================================
# STRING -- MEDIUM
# =========================================================================

add("str-m-01", "Longest Substring Without Repeating Characters", "String", "Medium",
    ["sliding-window", "hash-set"],
    "Given a string, find the length of the longest substring that "
    "contains no repeating characters.",
    ["0 <= length <= 5*10^4"],
    [{"input": "'abcabcbb'", "output": "3", "explanation": "'abc' is the longest substring without repetition"},
     {"input": "'bbbbb'", "output": "1"}],
    ["A sliding window with a set can track the current window's unique characters; shrink from the left when a duplicate appears.",
     "A hash map storing each character's last seen index lets you jump the left boundary directly instead of shrinking one step at a time."],
    {"time": "O(n)", "space": "O(min(n, alphabet size))"},
    ["How would you modify this to allow at most k repeating characters?",
     "How would you return the actual substring rather than just its length?"],
    ("LeetCode", "Longest Substring Without Repeating Characters"),
    ["Striver A2Z", "NeetCode 150", "Blind 75"])

add("str-m-02", "Group Anagrams", "String", "Medium",
    ["hash-map", "sorting"],
    "Given an array of strings, group the anagrams together. The order "
    "of groups, and of strings within a group, does not matter.",
    ["1 <= n <= 10^4"],
    [{"input": "['eat','tea','tan','ate','nat','bat']",
      "output": "[['eat','tea','ate'],['tan','nat'],['bat']]"}],
    ["Two strings are anagrams exactly when their sorted characters (or character-frequency signature) match.",
     "Use the sorted string (or a frequency-count tuple) as a hash map key, grouping all strings that share it."],
    {"time": "O(n * k log k)", "space": "O(n * k)"},
    ["How would using a frequency-count key instead of a sorted-string key change the time complexity?",
     "How would you group near-anagrams that differ by exactly one character?"],
    ("LeetCode", "Group Anagrams"),
    ["Striver A2Z", "NeetCode 150", "Blind 75"])

add("str-m-03", "Longest Palindromic Substring", "String", "Medium",
    ["expand-around-center", "dynamic-programming"],
    "Given a string, find the longest substring that is a palindrome.",
    ["1 <= length <= 1000"],
    [{"input": "'babad'", "output": "'bab'", "explanation": "'aba' is also a valid answer"},
     {"input": "'cbbd'", "output": "'bb'"}],
    ["Every palindrome expands outward from a center -- a single character (odd length) or between two characters (even length).",
     "Expanding around each of the 2n-1 possible centers gives O(n^2) time with O(1) space, avoiding the O(n^2) space of a full DP table."],
    {"time": "O(n^2)", "space": "O(1)"},
    ["How does Manacher's algorithm achieve O(n) time for this problem?",
     "How would you count all palindromic substrings instead of finding just the longest?"],
    ("LeetCode", "Longest Palindromic Substring"),
    ["Striver A2Z", "NeetCode 150", "Blind 75"])

add("str-m-04", "String to Integer (atoi)", "String", "Medium",
    ["string-parsing", "edge-cases"],
    "Implement a function that converts a string to a 32-bit signed "
    "integer, similar to C's atoi. Handle leading whitespace, an optional "
    "sign, digits up to the first non-digit character, and clamp to the "
    "32-bit signed range on overflow.",
    ["0 <= length <= 200"],
    [{"input": "'   -42'", "output": "-42"},
     {"input": "'4193 with words'", "output": "4193"},
     {"input": "'words and 987'", "output": "0"}],
    ["Work through the edge cases methodically: leading whitespace, an optional +/- sign, then consecutive digits, stopping at the first non-digit.",
     "Check for overflow before it happens -- compare against INT_MAX/10 before multiplying, rather than after overflowing."],
    {"time": "O(n)", "space": "O(1)"},
    ["What's the risk of checking for overflow after the multiplication instead of before?",
     "How would you adapt this to parse floating point numbers instead?"],
    ("LeetCode", "String to Integer (atoi)"),
    ["Striver A2Z"])

add("str-m-05", "Zigzag Conversion", "String", "Medium",
    ["simulation", "pattern-recognition"],
    "Given a string and a number of rows, write the string in a zigzag "
    "pattern across that many rows (top to bottom, then diagonally up, "
    "repeating), then read it off row by row and return the result.",
    ["1 <= length <= 1000", "1 <= numRows <= 1000"],
    [{"input": "s='PAYPALISHIRING', numRows=3", "output": "'PAHNAPLSIIGYIR'"},
     {"input": "s='PAYPALISHIRING', numRows=4", "output": "'PINALSIGYAHRPI'"}],
    ["Simulate directly: maintain one string per row, and step a 'current row' pointer down then up as you place each character.",
     "The direction flips exactly at row 0 and at row numRows-1."],
    {"time": "O(n)", "space": "O(n)"},
    ["Can you derive a direct index formula instead of simulating row by row?",
     "How would the pattern change for a zigzag with a different diagonal step size?"],
    ("LeetCode", "Zigzag Conversion"),
    ["NeetCode extension list"])

add("str-m-06", "Decode Ways", "String", "Medium",
    ["dynamic-programming"],
    "Given a string of digits (an encoding where 'A'=1 through 'Z'=26), "
    "count the number of ways it can be decoded back into letters.",
    ["1 <= length <= 100"],
    [{"input": "'12'", "output": "2", "explanation": "Can decode as 'AB' (1,2) or 'L' (12)"},
     {"input": "'226'", "output": "3", "explanation": "'BZ' (2,26), 'VF' (22,6), 'BBF' (2,2,6)"}],
    ["Think of it like climbing stairs: dp[i] depends on whether the single digit and/or the two-digit combination ending at i are valid.",
     "Watch out for '0' -- it's only valid as the second digit of a two-digit group (10 or 20), never standalone."],
    {"time": "O(n)", "space": "O(1) with rolling variables"},
    ["How would you extend this if decoding could also use a wildcard character representing any digit?",
     "How would you reconstruct one valid decoding, not just count them?"],
    ("LeetCode", "Decode Ways"),
    ["Striver A2Z", "NeetCode 150"])

add("str-m-07", "Palindromic Substrings (Count)", "String", "Medium",
    ["expand-around-center", "dynamic-programming"],
    "Given a string, count how many substrings of it are palindromes, "
    "counting different occurrences at different positions separately.",
    ["1 <= length <= 1000"],
    [{"input": "'abc'", "output": "3", "explanation": "'a','b','c' are the only palindromic substrings"},
     {"input": "'aaa'", "output": "6", "explanation": "'a','a','a','aa','aa','aaa'"}],
    ["This is closely related to Longest Palindromic Substring -- the same expand-around-center technique applies, just counting instead of tracking the max.",
     "Each of the 2n-1 centers contributes some number of palindromes as it expands outward."],
    {"time": "O(n^2)", "space": "O(1)"},
    ["How does Manacher's algorithm let you count all palindromic substrings in O(n)?",
     "How would you count only distinct palindromic substrings, ignoring position?"],
    ("LeetCode", "Palindromic Substrings"),
    ["NeetCode 150"])

add("str-m-08", "Letter Combinations of a Phone Number", "String", "Medium",
    ["backtracking"],
    "Given a string of digits from 2-9, return all possible letter "
    "combinations the number could represent, based on the standard "
    "telephone keypad mapping.",
    ["0 <= length <= 4"],
    [{"input": "'23'", "output": "['ad','ae','af','bd','be','bf','cd','ce','cf']"},
     {"input": "''", "output": "[]"}],
    ["Backtracking builds up one combination at a time: pick a letter for the current digit, recurse on the rest, then undo and try the next letter.",
     "The digit-to-letters mapping drives the branching factor at each recursive step."],
    {"time": "O(4^n * n) worst case", "space": "O(n)"},
    ["How would you generate combinations lazily (one at a time) instead of all at once, to save memory?",
     "How does this generalize to other keypad layouts, like a T9 predictive text mapping?"],
    ("LeetCode", "Letter Combinations of a Phone Number"),
    ["Striver A2Z", "NeetCode 150", "Blind 75"])

# =========================================================================
# STRING -- HARD
# =========================================================================

add("str-h-01", "Minimum Window Substring", "String", "Hard",
    ["sliding-window", "hash-map"],
    "Given two strings s and t, find the smallest substring of s that "
    "contains every character of t, including duplicates. Return an "
    "empty string if no such window exists.",
    ["1 <= s.length, t.length <= 10^5"],
    [{"input": "s='ADOBECODEBANC', t='ABC'", "output": "'BANC'"},
     {"input": "s='a', t='aa'", "output": "''", "explanation": "s doesn't contain two a's"}],
    ["Expand a right pointer to include characters until the window satisfies t's requirements, then contract from the left to find the minimal valid window.",
     "Track how many of t's required distinct characters are currently fully satisfied in the window, to know in O(1) when the window is valid."],
    {"time": "O(n+m)", "space": "O(m)"},
    ["How would you find the minimum window that contains at least one occurrence of each of several different target strings?",
     "How would you adapt this to a streaming version of s where you can't look back?"],
    ("LeetCode", "Minimum Window Substring"),
    ["Striver A2Z", "NeetCode 150", "Blind 75"])

add("str-h-02", "Regular Expression Matching", "String", "Hard",
    ["dynamic-programming", "recursion"],
    "Given a string s and a pattern p that may include '.' (matches any "
    "single character) and '*' (matches zero or more of the preceding "
    "element), implement matching that covers the entire input string.",
    ["1 <= s.length <= 20", "1 <= p.length <= 20"],
    [{"input": "s='aa', p='a*'", "output": "true", "explanation": "'*' means zero or more of the preceding 'a'"},
     {"input": "s='mississippi', p='mis*is*p*.'", "output": "false"}],
    ["Define dp[i][j] as whether s[0:i] matches p[0:j], and think through the transitions for a normal character, '.', and '*' separately.",
     "The '*' case has two sub-cases: treating the preceding element as occurring zero times, or matching one more occurrence and staying on the same pattern position."],
    {"time": "O(n*m)", "space": "O(n*m)"},
    ["How would you extend this to also support '+' and '?' quantifiers?",
     "How does this relate to building an NFA for regex matching?"],
    ("LeetCode", "Regular Expression Matching"),
    ["Striver A2Z", "Blind 75"])

add("str-h-03", "Text Justification", "String", "Hard",
    ["greedy", "simulation"],
    "Given an array of words and a maximum line width, format the text so "
    "each line has exactly that width, with words packed greedily and "
    "extra spaces distributed as evenly as possible (left-heavy when "
    "uneven). The last line should be left-justified with single spaces "
    "and padded with trailing spaces.",
    ["1 <= words.length <= 300", "1 <= maxWidth <= 100"],
    [{"input": "words=['This','is','an','example','of','text','justification.'], maxWidth=16",
      "output": "['This    is    an','example  of text','justification.  ']"}],
    ["Greedily fit as many words as possible on each line before deciding how to distribute the spaces.",
     "Handle three cases separately: a full line with multiple words, a line with only one word, and the final line."],
    {"time": "O(total characters)", "space": "O(total characters)"},
    ["How would you handle a target width that varies per line (e.g. for a trapezoidal layout)?",
     "How would you adapt this for right-to-left text justification?"],
    ("LeetCode", "Text Justification"),
    ["Blind 75"])

# =========================================================================
# LINKED LIST -- EASY
# =========================================================================

add("ll-e-01", "Reverse Linked List", "Linked List", "Easy",
    ["pointer-manipulation"],
    "Given the head of a singly linked list, reverse the list in-place "
    "and return the new head.",
    ["0 <= n <= 5000"],
    [{"input": "1->2->3->4->5", "output": "5->4->3->2->1"},
     {"input": "1->2", "output": "2->1"}],
    ["Track three pointers as you walk the list -- previous, current, and next -- re-linking one node at a time.",
     "Can you also express this recursively, reversing the rest of the list first and then fixing the current node's links?"],
    {"time": "O(n)", "space": "O(1) iterative / O(n) recursive"},
    ["How would you reverse only a sublist between positions m and n?",
     "How would you reverse the list in groups of k nodes?"],
    ("LeetCode", "Reverse Linked List"),
    ["Striver A2Z", "NeetCode 150", "Blind 75"])

add("ll-e-02", "Merge Two Sorted Lists", "Linked List", "Easy",
    ["two-pointer", "dummy-node"],
    "Given the heads of two sorted linked lists, merge them into one "
    "sorted list by splicing together the existing nodes, and return the head.",
    ["0 <= n, m <= 50"],
    [{"input": "l1=1->2->4, l2=1->3->4", "output": "1->1->2->3->4->4"},
     {"input": "l1=[], l2=[]", "output": "[]"}],
    ["A dummy head node simplifies edge cases so you don't need special logic for the very first node.",
     "At each step, attach whichever current node (from l1 or l2) has the smaller value, then advance that list's pointer."],
    {"time": "O(n+m)", "space": "O(1)"},
    ["How would you merge k sorted lists efficiently, not just two?",
     "How would you merge two sorted doubly linked lists?"],
    ("LeetCode", "Merge Two Sorted Lists"),
    ["Striver A2Z", "NeetCode 150", "Blind 75"])

add("ll-e-03", "Linked List Cycle", "Linked List", "Easy",
    ["floyd-cycle-detection", "two-pointer"],
    "Given the head of a linked list, determine whether the list contains "
    "a cycle (a node reachable again by following next pointers).",
    ["0 <= n <= 10^4"],
    [{"input": "3->2->0->-4 (tail connects back to the node at index 1)", "output": "true"},
     {"input": "1->2 (no cycle)", "output": "false"}],
    ["A hash set of visited nodes works but uses O(n) space -- can you detect a cycle in O(1) space?",
     "Floyd's tortoise and hare: a slow pointer moving one step and a fast pointer moving two steps will eventually meet if and only if a cycle exists."],
    {"time": "O(n)", "space": "O(1)"},
    ["How would you find the node where the cycle begins, not just detect that one exists?",
     "How would you find the length of the cycle once detected?"],
    ("LeetCode", "Linked List Cycle"),
    ["Striver A2Z", "NeetCode 150", "Blind 75"])

add("ll-e-04", "Middle of the Linked List", "Linked List", "Easy",
    ["slow-fast-pointer"],
    "Given the head of a singly linked list, return the middle node. If "
    "there are two middle nodes (even length), return the second one.",
    ["1 <= n <= 100"],
    [{"input": "1->2->3->4->5", "output": "3 (node with value 3)"},
     {"input": "1->2->3->4->5->6", "output": "4 (node with value 4)"}],
    ["A two-pass approach (count then walk) works but visits the list twice -- can you find the middle in one pass?",
     "A fast pointer moving two steps for every one step of a slow pointer lands the slow pointer at the middle when the fast pointer reaches the end."],
    {"time": "O(n)", "space": "O(1)"},
    ["How would you modify this to return the first middle node instead of the second for even-length lists?",
     "How would you delete the middle node directly using this same technique?"],
    ("LeetCode", "Middle of the Linked List"),
    ["NeetCode 150", "Striver A2Z"])

add("ll-e-05", "Palindrome Linked List", "Linked List", "Easy",
    ["slow-fast-pointer", "reversal"],
    "Given the head of a singly linked list, determine whether it reads "
    "the same forwards and backwards.",
    ["1 <= n <= 10^5"],
    [{"input": "1->2->2->1", "output": "true"},
     {"input": "1->2", "output": "false"}],
    ["Copying values into an array lets you check with two pointers in O(n) space -- can you do it in O(1) space instead?",
     "Find the middle with slow/fast pointers, reverse the second half in-place, then compare it against the first half."],
    {"time": "O(n)", "space": "O(1)"},
    ["If you reverse the second half in-place to solve this, how would you restore the list to its original structure afterward?",
     "How would you solve this for a doubly linked list more simply?"],
    ("LeetCode", "Palindrome Linked List"),
    ["Striver A2Z", "NeetCode 150"])

# =========================================================================
# LINKED LIST -- MEDIUM
# =========================================================================

add("ll-m-01", "Remove Nth Node From End of List", "Linked List", "Medium",
    ["two-pointer", "dummy-node"],
    "Given the head of a linked list, remove the n-th node from the end "
    "of the list and return the head, doing so in a single pass.",
    ["1 <= n <= sz <= 30"],
    [{"input": "1->2->3->4->5, n=2", "output": "1->2->3->5"},
     {"input": "1, n=1", "output": "[] (empty list)"}],
    ["A two-pass approach (get length, then walk to the right spot) is straightforward -- can you do it in one pass?",
     "Advance a fast pointer n steps ahead first, then move both fast and slow together; when fast reaches the end, slow is just before the node to remove."],
    {"time": "O(n)", "space": "O(1)"},
    ["How would you handle removing the n-th node from the front instead?",
     "How would you adapt this to a doubly linked list, and would it get simpler?"],
    ("LeetCode", "Remove Nth Node From End of List"),
    ["Striver A2Z", "NeetCode 150", "Blind 75"])

add("ll-m-02", "Reorder List", "Linked List", "Medium",
    ["slow-fast-pointer", "reversal", "merge"],
    "Given the head of a singly linked list L0 -> L1 -> ... -> Ln, "
    "reorder it in-place to L0 -> Ln -> L1 -> Ln-1 -> L2 -> Ln-2 -> ...",
    ["1 <= n <= 5*10^4"],
    [{"input": "1->2->3->4", "output": "1->4->2->3"},
     {"input": "1->2->3->4->5", "output": "1->5->2->4->3"}],
    ["Break the problem into three steps: find the middle, reverse the second half, then merge the two halves by alternating nodes.",
     "Each of the three sub-steps is a classic pattern you may have solved separately before."],
    {"time": "O(n)", "space": "O(1)"},
    ["How would you reorder into a different alternating pattern, e.g. three-way interleaving?",
     "What changes if the list is circular?"],
    ("LeetCode", "Reorder List"),
    ["Striver A2Z", "NeetCode 150", "Blind 75"])

add("ll-m-03", "Add Two Numbers", "Linked List", "Medium",
    ["linked-list-arithmetic", "carry-propagation"],
    "Given two non-empty linked lists representing two non-negative "
    "integers with digits stored in reverse order (each node holds a "
    "single digit), add the two numbers and return the sum as a linked "
    "list in the same reversed-digit format.",
    ["1 <= n, m <= 100", "0 <= digit <= 9"],
    [{"input": "l1=2->4->3, l2=5->6->4", "output": "7->0->8", "explanation": "342 + 465 = 807"},
     {"input": "l1=0, l2=0", "output": "0"}],
    ["Walk both lists simultaneously, adding corresponding digits plus any carry from the previous step, creating a new node for each resulting digit.",
     "Don't forget to handle lists of different lengths, and a possible final carry after both lists are exhausted."],
    {"time": "O(max(n,m))", "space": "O(max(n,m))"},
    ["How would this change if the digits were stored in forward (most-significant-first) order instead?",
     "How would you add more than two numbers represented this way?"],
    ("LeetCode", "Add Two Numbers"),
    ["Striver A2Z", "NeetCode 150", "Blind 75"])

add("ll-m-04", "Copy List with Random Pointer", "Linked List", "Medium",
    ["hash-map", "interleaving"],
    "Given a linked list where each node has a next pointer and an "
    "additional random pointer that can point to any node in the list or "
    "to null, create a deep copy of the list.",
    ["0 <= n <= 1000"],
    [{"input": "[[7,null],[13,0],[11,4],[10,2],[1,0]]",
      "output": "a structurally identical deep copy with random pointers correctly re-mapped to the new nodes"}],
    ["A hash map from original node to its copy lets you resolve both next and random pointers in a second pass -- O(n) space.",
     "For O(1) extra space, interleave copied nodes directly after their originals (A->A'->B->B'->...), use that interleaving to set random pointers, then unweave the two lists."],
    {"time": "O(n)", "space": "O(n) with hash map, O(1) with interleaving"},
    ["Walk through why the interleaving trick lets you set each copy's random pointer correctly.",
     "How would you extend this to a node whose random pointer can point into a *different* list?"],
    ("LeetCode", "Copy List with Random Pointer"),
    ["Striver A2Z", "NeetCode 150", "Blind 75"])

add("ll-m-05", "Odd Even Linked List", "Linked List", "Medium",
    ["pointer-manipulation", "in-place"],
    "Given the head of a singly linked list, group all nodes at odd "
    "indices together followed by all nodes at even indices (1-indexed, "
    "preserving each group's relative order), in-place with O(1) extra space.",
    ["0 <= n <= 10^4"],
    [{"input": "1->2->3->4->5", "output": "1->3->5->2->4"},
     {"input": "2->1->3->5->6->4->7", "output": "2->3->6->7->1->5->4"}],
    ["Maintain two separate chains (odd and even) as you walk the list once, then splice the even chain onto the end of the odd chain.",
     "Keep a saved reference to the even chain's head before rewiring pointers, or you'll lose track of where to splice it back in."],
    {"time": "O(n)", "space": "O(1)"},
    ["How would this generalize to grouping nodes by index mod k instead of just odd/even?",
     "How would you solve this for a doubly linked list?"],
    ("LeetCode", "Odd Even Linked List"),
    ["NeetCode 150"])

add("ll-m-06", "Rotate List", "Linked List", "Medium",
    ["pointer-manipulation", "circular-linking"],
    "Given the head of a linked list, rotate the list to the right by k places.",
    ["0 <= n <= 500", "0 <= k <= 2*10^9"],
    [{"input": "1->2->3->4->5, k=2", "output": "4->5->1->2->3"},
     {"input": "0->1->2, k=4", "output": "2->0->1"}],
    ["First find the list's length so you can reduce k modulo length -- rotating by the full length is a no-op.",
     "Connect the tail to the head to form a temporary circle, then break it at the correct new starting point."],
    {"time": "O(n)", "space": "O(1)"},
    ["How would you rotate left instead of right?",
     "How would you handle this if k were given as a live stream and could change after each query?"],
    ("LeetCode", "Rotate List"),
    ["Striver A2Z", "NeetCode 150"])

add("ll-m-07", "Swap Nodes in Pairs", "Linked List", "Medium",
    ["pointer-manipulation", "dummy-node"],
    "Given a linked list, swap every two adjacent nodes and return the "
    "head, without modifying the values inside the nodes -- only the "
    "links may change.",
    ["0 <= n <= 100"],
    [{"input": "1->2->3->4", "output": "2->1->4->3"},
     {"input": "1", "output": "1"}],
    ["A dummy node before the head simplifies keeping track of the node just before each pair being swapped.",
     "For each pair, carefully re-point three links in the right order so you don't lose the reference to the rest of the list."],
    {"time": "O(n)", "space": "O(1) iterative"},
    ["How would you generalize this to swapping nodes in groups of k?",
     "Can you write a clean recursive version, and how does its space complexity compare to the iterative one?"],
    ("LeetCode", "Swap Nodes in Pairs"),
    ["Striver A2Z", "NeetCode 150"])

add("ll-m-08", "Partition List", "Linked List", "Medium",
    ["two-pointer", "dummy-node"],
    "Given the head of a linked list and a value x, partition it so all "
    "nodes less than x come before all nodes greater than or equal to x, "
    "preserving the original relative order within each partition.",
    ["0 <= n <= 200"],
    [{"input": "1->4->3->2->5->2, x=3", "output": "1->2->2->4->3->5"},
     {"input": "2->1, x=2", "output": "1->2"}],
    ["Build two separate lists (values < x, and values >= x) as you walk through once, then join them at the end.",
     "Using dummy heads for both sublists avoids special-casing whichever list ends up empty."],
    {"time": "O(n)", "space": "O(1)"},
    ["How would you partition into three groups instead of two (less than, equal to, greater than x)?",
     "How does this compare to the partition step in quicksort on an array?"],
    ("LeetCode", "Partition List"),
    ["Striver A2Z"])

# =========================================================================
# LINKED LIST -- HARD
# =========================================================================

add("ll-h-01", "Merge k Sorted Lists", "Linked List", "Hard",
    ["heap", "divide-and-conquer"],
    "Given an array of k sorted linked lists, merge them all into one "
    "sorted linked list and return its head.",
    ["0 <= k <= 10^4", "total nodes across all lists <= 10^4"],
    [{"input": "lists=[1->4->5, 1->3->4, 2->6]", "output": "1->1->2->3->4->4->5->6"},
     {"input": "lists=[]", "output": "[]"}],
    ["Merging lists two at a time sequentially works but costs O(kn) total -- a min-heap over the current front of each list gets you to O(n log k).",
     "Divide-and-conquer (pairwise merging, halving the number of lists each round) reaches the same O(n log k) bound without an explicit heap."],
    {"time": "O(n log k)", "space": "O(k)"},
    ["How do the heap-based and divide-and-conquer approaches compare in practice for very large k?",
     "How would you merge k sorted lists if they were extremely large and stored on disk?"],
    ("LeetCode", "Merge k Sorted Lists"),
    ["Striver A2Z", "NeetCode 150", "Blind 75"])

add("ll-h-02", "Reverse Nodes in k-Group", "Linked List", "Hard",
    ["pointer-manipulation", "recursion"],
    "Given the head of a linked list, reverse the nodes in groups of k "
    "and return the modified list. If the number of remaining nodes is "
    "not a multiple of k, leave the final group as-is.",
    ["1 <= n <= 5000", "1 <= k <= n"],
    [{"input": "1->2->3->4->5, k=2", "output": "2->1->4->3->5"},
     {"input": "1->2->3->4->5, k=3", "output": "3->2->1->4->5"}],
    ["First check whether at least k nodes remain -- if not, leave that final segment unreversed.",
     "Reversing a group is the same pointer-manipulation as reversing a whole list; the harder part is correctly re-linking each group's boundary to the next."],
    {"time": "O(n)", "space": "O(1) iterative / O(n/k) recursive"},
    ["How would you reverse the list in groups of k while leaving every other group untouched?",
     "What's the trade-off between the iterative and recursive implementations here?"],
    ("LeetCode", "Reverse Nodes in k-Group"),
    ["Striver A2Z", "NeetCode 150", "Blind 75"])

add("ll-h-03", "LRU Cache", "Linked List", "Hard",
    ["hash-map", "doubly-linked-list", "design"],
    "Design a data structure that implements a Least Recently Used (LRU) "
    "cache. It should support get and put operations in O(1) average "
    "time, evicting the least recently used entry when capacity is exceeded.",
    ["1 <= capacity <= 3000", "0 <= key, value <= 10^4", "at most 2*10^5 operations"],
    [{"input": "capacity=2; put(1,1); put(2,2); get(1); put(3,3) evicts key 2; get(2)",
      "output": "get(1) -> 1, get(2) -> -1"}],
    ["A hash map alone gives O(1) lookup but no ordering; a linked list alone gives ordering but O(n) lookup -- combine both.",
     "A doubly linked list lets you move a node to the front (mark as recently used) or remove the tail (evict) in O(1), while the hash map gives O(1) access to any node by key."],
    {"time": "O(1) average per operation", "space": "O(capacity)"},
    ["How would you design an LFU (Least Frequently Used) cache instead, and how does the data structure combination change?",
     "How would you make this cache thread-safe under concurrent access?"],
    ("LeetCode", "LRU Cache"),
    ["Striver A2Z", "NeetCode 150", "Blind 75"])

# =========================================================================
# Output
# =========================================================================

assert len(PROBLEMS) == 50, f"Expected 50 problems, got {len(PROBLEMS)}"

by_topic = {}
by_difficulty = {}
for p in PROBLEMS:
    by_topic[p["topic"]] = by_topic.get(p["topic"], 0) + 1
    by_difficulty[p["difficulty"]] = by_difficulty.get(p["difficulty"], 0) + 1

output = {
    "metadata": {
        "title": "DSA Interview Question Bank v0",
        "generated_on": str(date.today()),
        "total_problems": len(PROBLEMS),
        "counts_by_topic": by_topic,
        "counts_by_difficulty": by_difficulty,
        "topics": ["Array", "String", "Linked List"],
        "difficulty_order": ["Easy", "Medium", "Hard"],
        "escalation_note": (
            "Escalation (harder follow-up problem after a strong solve) is selection logic, "
            "not data: pick another problem with the same topic and the next entry in "
            "difficulty_order, excluding the current problem id. follow_up_questions is a "
            "separate, unrelated concept -- depth-probing prompts about the *current* problem "
            "(e.g. 'what if the array is sorted?'), not a link to another problem."
        ),
        "sourcing_methodology": (
            "Problem selection uses Striver's A2Z Sheet as the topic/pattern "
            "skeleton for Arrays, Strings, and Linked Lists, cross-validated "
            "against NeetCode 150 and Blind 75 for interview relevance. "
            "All problem_statement, constraints, examples, and hints text is "
            "written originally for this platform -- none of it is copied "
            "from LeetCode, GeeksforGeeks, or any other source. "
            "source_reference and prep_sheets_seen_on fields are attribution "
            "pointers only (platform + canonical problem name), intended for "
            "linking out to further practice, not for embedding external content."
        ),
        "schema_notes": {
            "patterns": "Algorithmic technique tags, useful for filtering/spaced-repetition.",
            "optimal_complexity": "Time/space complexity of the expected optimal solution.",
            "follow_up_questions": "Suggested prompts for an AI interviewer to ask after a correct solution, to probe depth.",
            "prep_sheets_seen_on": "Well-known public curricula this problem is commonly associated with, for cross-reference only."
        }
    },
    "problems": PROBLEMS,
}

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"Wrote {len(PROBLEMS)} problems to {OUTPUT_PATH}")
print("By topic:", by_topic)
print("By difficulty:", by_difficulty)