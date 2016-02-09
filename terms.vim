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
syn match paren  "[()]"
syn match comma  ","
syn match dot  "\."
syn match verb "([a-z0-9_-]\+\>" contains=paren,var
syn match label ",\s\+[a-z_-]\+\>" contains=comma
syn match verbdef "^to [a-z0-9_-]\+ is to [a-z0-9_-]\+" contains=is,to
syn match defn "[a-z0-9_-]\+\s\+is\>" contains=is
syn match mod "\<[a-z0-9_-]\+\s*[,.)]"me=e-1
syn match modef "\<[a-z_-]\+\s\+a\s\+" contains=a

syn keyword import  import
syn keyword is  is
syn keyword to  to
syn keyword a  a

syn match var  "\<[A-Z][A-Za-z_-]*[0-9]\+\>"

syn match termsUri /<[^>]\+>/

syn region termsMeta start=/{{{/ end=/}}}/

hi link import Statement
hi link termsUri String
hi link termsMeta String


highlight link comment Comment
highlight link is Statement
highlight link to Statement
highlight link comma Statement
highlight link dot Statement
highlight link a Statement
highlight link paren Statement

highlight link mod Question
highlight link var Function

highlight link defn NonText
highlight link verb String
highlight link verbdef NonText

highlight link label Operator
highlight link modef Operator

let b:current_syntax="terms"
