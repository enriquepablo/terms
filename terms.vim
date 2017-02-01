" Vim syntax file
" Language:     Juliet's todo files
" Maintainer:   Juliet Kemp 
" Last Change:  Sept 14, 2011
" Version:      1

if exists("b:current_syntax")
  finish
endif

setlocal iskeyword+="-"
syn case match

syn include @python syntax/python.vim
syn region pythonSnip matchgroup=Snip start="<-" end="->" contains=@python
hi link Snip SpecialComment

syn match comment  "^#.*$"
syn match rparen  ")"
syn match lparen  "(" contained
syn match comma  ","
syn match dot  "\."
syn match semicolon  ";"
syn match colon  ":"
syn match implies  "\(-\)\@<!->"
syn keyword is is contained

" facts
syn match verb "([A-Z]\?[A-Za-z0-9_-]\+\>" contains=lparen,var
syn match prep "\(,\)\@<=\s\+[a-z]\+\>\(\s\+a\>\)\@!"
syn match modif "\(\<a\>\)\@<!\s\+[A-Z]\?[A-Za-z0-9_-]\+[,)]" contains=comma,rparen,var

syn match factvar "\<[A-Z][A-Za-z0-9_-]\+:\((\)\@=" contains=lparen,var

" verb defns
syn match verbdef "^to\s\+[a-z0-9_-]\+\s\+" contains=to
syn match verbsup "\<is\s\+to\s\+[a-z0-9_-]\+" contains=to,is
syn match prepdef "\<[a-z]\+\s\+\(a\s\+\)\@="
syn match modef "\<a\s\+[A-Z]\?[:A-Za-z0-9_-]\+\(\s*[,.\n]\)\@=" contains=a,var

" name defns
syn match defnoun "^a\s\+[A-Z]\?[A-Za-z0-9_-]\+\s\+is\s\+\(a\>\)\@=" contains=a,is,var

" noun defns
syn match defname "^[A-Z]\?[A-Za-z0-9_-]\+\s\+is\s\+\(a\>\)\@=" contains=is,var

syn keyword import  import
syn keyword to  to contained
syn keyword a  a contained

syn match var  "\<[A-Z][A-Za-z_-]*[0-9]\+\>" contained

syn match termsUri /<[^>]\+>/

syn region termsMeta start=/{{{/ end=/}}}/

hi link import Debug
hi link termsUri String
hi link termsMeta String


highlight link comment Comment
highlight link is Delimiter
highlight link to Delimiter
highlight link a Delimiter
highlight link implies Exception
highlight link comma Debug
highlight link semicolon Debug
highlight link dot Debug
highlight link lparen Debug
highlight link rparen Debug

highlight link modif SpecialComment
highlight link modef Debug
highlight link var Constant

" highlight link defn Special
highlight link verb Label
highlight link verbdef Macro
highlight link verbsup Special

highlight link prep Keyword
highlight link prepdef SpecialChar

highlight link defnoun WarningMsg
highlight link defname WarningMsg
highlight link prepdef PreProc

let b:current_syntax="terms"
